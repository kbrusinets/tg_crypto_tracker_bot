import itertools
import traceback
from typing import Dict, Set, Optional
from datetime import datetime as dt

from services.notification_formatting.service import NotificationFormattingService
from services.chain.service import ChainsService
from services.chain.supported_chains.bsc import BSC
from schemas import TransactionInfo, ParsedNotification, WalletAddToTrack
from services.db.service import DbService
from utils.singleton import Singleton


class Backend(metaclass=Singleton):
    def __init__(self):
        self.chains = [BSC()]
        self.chains_service = ChainsService(chains=self.chains)
        self.db_service = DbService()
        self.notification_formatting_service = NotificationFormattingService(
            chains_service=self.chains_service,
            db_service=self.db_service
        )

    async def start(self):
        await self.db_service.start(self.chains)

    def get_transaction_wallets(self, tran: TransactionInfo) -> Set[str]:
        wallets_involved = set()
        wallets_involved.update((tran.from_, tran.to_))
        for int_tran in tran.internal_transactions:
            wallets_involved.update((int_tran.from_, int_tran.to_))
        for tok_transf in tran.token_transfers:
            wallets_involved.update((tok_transf.from_, tok_transf.to_))
        if None in wallets_involved:
            wallets_involved.remove(None)
        return wallets_involved

    async def monitor(self):
        async for notif in self.chains_service.monitor():
            try:
                for tran in notif.transactions:
                    wallets_involved = self.get_transaction_wallets(tran)
                    users_trackings_map = await self.db_service.check_who_tracks_wallets(
                        chain_key=notif.chain_key,
                        wallets_involved=wallets_involved)
                    if users_trackings_map:
                        tx_receipt = await self.chains_service.get_transaction_receipt(chain_key=notif.chain_key, tx_hash=tran.hash)
                        if tx_receipt['result']['status'] != '0x1':
                            continue
                        for user in users_trackings_map.keys():
                            user_notification = await self.notification_formatting_service.parse_notification(
                                chain_key=notif.chain_key,
                                user_id=user,
                                transaction=tran,
                                wallets_monitored=users_trackings_map[user]
                            )
                            await self.autoadd_tracking(
                                notif=user_notification,
                                wallets_monitored=users_trackings_map[user]
                            )
                            yield user_notification
            except Exception as error:
                print(f'{dt.now()} Unexpected error while processing notification.')
                print(f'{dt.now()} {traceback.format_exc()}')

    async def autoadd_tracking(self,
                               notif: ParsedNotification,
                               wallets_monitored: Dict[str, str]):
        to_wallets = set()
        if notif.base_tran:
            base_tran = [notif.base_tran]
        else:
            base_tran = []
        for transfer in itertools.chain(base_tran, notif.internal_transactions, notif.token_transfers):
            if transfer.from_.address in wallets_monitored and transfer.to_.address not in wallets_monitored:
                to_wallets.add(transfer.to_.address)
        for wallet in to_wallets:
            trans_amount = await self.get_all_transactions_amount(chain_key=notif.chain_key, address=wallet)
            days_since_first_trans = await self.get_days_since_first_trans(chain_key=notif.chain_key, address=wallet)
            avg_txs_per_day = trans_amount / (days_since_first_trans or 1)
            if avg_txs_per_day < 5:
                await self.db_service.add_wallet_tracking(chain_key=notif.chain_key, user_id=notif.user_id, wallet_address=wallet)
                notif.autoadded_wallets.append(
                    WalletAddToTrack(
                        address=wallet,
                        reason=f'avg txs per day = {"{:.2f}".format(avg_txs_per_day)}'
                    )
                )
            else:
                if days_since_first_trans < 5:
                    await self.db_service.add_wallet_tracking(chain_key=notif.chain_key, user_id=notif.user_id, wallet_address=wallet)
                    notif.autoadded_wallets.append(
                        WalletAddToTrack(
                            address=wallet,
                            reason=f'days since first trans = {days_since_first_trans}'
                        )
                    )
                else:
                    notif.wallets_to_ask.append(
                        WalletAddToTrack(
                            address=wallet,
                            reason=f'avg txs per day = {"{:.2f}".format(avg_txs_per_day)}, days since first trans = {days_since_first_trans}'
                        )
                    )

    def get_chains_keys(self):
        return self.chains_service.get_chains_keys()

    async def format_notification(self, notif: ParsedNotification):
        try:
            return await self.notification_formatting_service.format_notification(notif=notif)
        except Exception as error:
            print(f'{dt.now()} Unexpected error while parsing notification.')
            print(f'{dt.now()} {notif}')
            return None

    async def get_all_transactions_amount(self, chain_key: str, address: str):
        normal_transactions = await self.chains_service.get_amount_of_normal_transactions(chain_key=chain_key, address=address)
        token_transactions = await self.chains_service.get_amount_of_token_transactions(chain_key=chain_key, address=address)
        return normal_transactions + token_transactions

    async def get_days_since_first_trans(self, chain_key: str, address: str) -> int:
        first_transaction_ts = await self.chains_service.get_first_transaction_ts(chain_key=chain_key, address=address)
        if first_transaction_ts is None:
            return 0
        now_ts = int(dt.now().timestamp())
        day = 86400
        return int((now_ts - first_transaction_ts) / day)

    async def give_wallet_a_name(self, chain_key: str, user_id: int, wallet_address: str, wallet_name: str):
        return await self.db_service.give_wallet_a_name(chain_key=chain_key,
                                                        user_id=user_id,
                                                        wallet_address=wallet_address,
                                                        wallet_name=wallet_name)

    async def get_wallet_name(self, chain_key: str, user_id: int, wallet_address: str):
        return await self.db_service.get_wallet_name(chain_key=chain_key,
                                                     user_id=user_id,
                                                     wallet_address=wallet_address)

    async def get_user_trackings(self, chain_key: str, user_id: int, wallet_address: str = None, custom_name: str = None):
        return await self.db_service.get_user_trackings(chain_key=chain_key,
                                                        user_id=user_id,
                                                        wallet_address=wallet_address,
                                                        custom_name=custom_name)

    async def stop_wallet_tracking(self, chain_key: str, user_id: int, wallet_address: Optional[str] = None):
        return await self.db_service.stop_wallet_tracking(chain_key=chain_key,
                                                          user_id=user_id,
                                                          wallet_address=wallet_address)

    async def add_wallet_tracking(self, chain_key: str, user_id: int, wallet_address: str):
        return await self.db_service.add_wallet_tracking(chain_key=chain_key,
                                                         user_id=user_id,
                                                         wallet_address=wallet_address)
