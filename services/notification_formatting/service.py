from typing import Dict

from web3.contract import Contract

from schemas import ParsedCoinTransfer, ParsedTokenTransfer, WalletAddToTrack, ParsedNotification, TransactionInfo, \
    ParsedWallet
import aiogram.utils.markdown as fmt

from services.chain.service import ChainsService
from services.db.service import DbService
from utils.utils import trim_address, float_to_str
from emoji import emojize


class NotificationFormattingService:
    def __init__(self, chains_service: ChainsService, db_service: DbService):
        self.chains_service = chains_service
        self.db_service = db_service

    def create_transfer_string(self, chain_key: str, transfer: [ParsedCoinTransfer, ParsedTokenTransfer], currency: str,
                               currency_contract: str = None):
        to_ = transfer.to_.address
        from_ = transfer.from_.address

        return fmt.text(
            '▸',
            fmt.bold('From'),
            fmt.link(trim_address(from_),
                     self.chains_service.get_scan_wallet_link(chain_key=chain_key, address=from_)) +
            ((fmt.escape_md(f' ({transfer.from_.custom_name})') if transfer.from_.custom_name else emojize(
                ' :pushpin:')) if transfer.from_.monitored else ''),
            fmt.bold('To'),
            fmt.link(trim_address(to_), self.chains_service.get_scan_wallet_link(chain_key=chain_key, address=to_)) +
            ((fmt.escape_md(f' ({transfer.to_.custom_name})') if transfer.to_.custom_name else emojize(
                ' :pushpin:')) if transfer.to_.monitored else ''),
            fmt.bold('For'),
            fmt.escape_md(transfer.amount),
            fmt.link(currency, self.chains_service.get_scan_wallet_link(chain_key=chain_key,
                                                                        address=currency_contract)) if currency_contract else currency
        )

    def create_autoadded_wallet_string(self, chain_key: str, wallet: WalletAddToTrack):
        return fmt.text(
            fmt.text(
                fmt.link(trim_address(wallet.address),
                         self.chains_service.get_scan_wallet_link(chain_key=chain_key, address=wallet.address)),
                fmt.bold('added to tracking'),
                fmt.escape_md(f'({wallet.reason})')
            ),
            fmt.escape_md(f'Rename: /rn_{chain_key}_{wallet.address}'),
            sep='\n'
        )

    def create_wallets_to_ask_string(self, chain_key: str, wallet: WalletAddToTrack):
        return fmt.text(
            fmt.text(
                fmt.link(trim_address(wallet.address),
                         self.chains_service.get_scan_wallet_link(chain_key=chain_key, address=wallet.address)),
                fmt.escape_md(f'({wallet.reason})')
            ),
            fmt.escape_md(f'Add: /add_{chain_key}_{wallet.address}'),
            sep='\n'
        )

    async def format_notification(self, notif: ParsedNotification):
        message_parts = []
        message_parts.append(fmt.text(
            emojize(':memo:'),
            fmt.link('Transaction',
                     self.chains_service.get_scan_tx_link(chain_key=notif.chain_key, tx_hash=notif.tx_hash)),
            fmt.bold(self.chains_service.get_chain_info(chain_key=notif.chain_key).name)
        ))
        if notif.base_tran:
            message_parts.append(
                self.create_transfer_string(
                    chain_key=notif.chain_key,
                    transfer=notif.base_tran,
                    currency=await self.db_service.get_native_coin(notif.chain_key)
                )
            )
        for int_tran in notif.internal_transactions:
            message_parts.append(
                self.create_transfer_string(
                    chain_key=notif.chain_key,
                    transfer=int_tran,
                    currency=await self.db_service.get_native_coin(notif.chain_key)
                )
            )
        for token_trans in notif.token_transfers:
            message_parts.append(
                self.create_transfer_string(
                    chain_key=notif.chain_key,
                    transfer=token_trans,
                    currency=token_trans.token_symbol,
                    currency_contract=token_trans.token_address
                )
            )
        if notif.autoadded_wallets:
            message_parts.append('———————')
            for item in notif.autoadded_wallets:
                message_parts.append(self.create_autoadded_wallet_string(chain_key=notif.chain_key, wallet=item))
        if notif.wallets_to_ask:
            message_parts.append('———————')
            message_parts.append(fmt.bold('Wallets to consider:'))
            for item in notif.wallets_to_ask:
                message_parts.append(self.create_wallets_to_ask_string(chain_key=notif.chain_key, wallet=item))
        if len(message_parts) == 1:
            return None
        else:
            return fmt.text(*message_parts, sep='\n\n')

    def parse_notification(self,
                           chain_key: str,
                           user_id: int,
                           transaction: TransactionInfo,
                           wallets_monitored: Dict[str, str],
                           token_contracts: Dict[str, Contract]) -> ParsedNotification:
        value_mult = 10 ** (-18)
        base_tran = None
        internal_transactions = []
        token_transfers = []
        if transaction.from_ in wallets_monitored.keys() or transaction.to_ in wallets_monitored.keys():
            base_tran = ParsedCoinTransfer(
                from_=ParsedWallet(
                    address=transaction.from_,
                    monitored=transaction.from_ in wallets_monitored,
                    custom_name=wallets_monitored[transaction.from_] if transaction.from_ in wallets_monitored else None
                ),
                to_=ParsedWallet(
                    address=transaction.to_,
                    monitored=transaction.to_ in wallets_monitored,
                    custom_name=wallets_monitored[transaction.to_] if transaction.to_ in wallets_monitored else None
                ),
                amount=float_to_str(int(transaction.value, 16) * value_mult)
            )
        for tran in transaction.internal_transactions:
            if tran.from_ in wallets_monitored or tran.to_ in wallets_monitored:
                internal_transactions.append(
                    ParsedCoinTransfer(
                        from_=ParsedWallet(
                            address=tran.from_,
                            monitored=tran.from_ in wallets_monitored.keys(),
                            custom_name=wallets_monitored[tran.from_] if tran.from_ in wallets_monitored else None
                        ),
                        to_=ParsedWallet(
                            address=tran.to_,
                            monitored=tran.to_ in wallets_monitored.keys(),
                            custom_name=wallets_monitored[tran.to_] if tran.to_ in wallets_monitored else None
                        ),
                        amount=float_to_str(int(tran.value) * value_mult)
                    )
                )
        for token_transfer in transaction.token_transfers:
            if token_transfer.from_ in wallets_monitored or token_transfer.to_ in wallets_monitored:
                contract = token_contracts[token_transfer.contract_address]
                if contract is None or 'symbol' not in contract.functions:
                    token_symbol = 'Unknown token'
                else:
                    token_symbol = contract.functions.symbol().call()
                token_transfers.append(
                    ParsedTokenTransfer(
                        from_=ParsedWallet(
                            address=token_transfer.from_,
                            monitored=token_transfer.from_ in wallets_monitored.keys(),
                            custom_name=wallets_monitored[token_transfer.from_] if token_transfer.from_ in wallets_monitored else None
                        ),
                        to_=ParsedWallet(
                            address=token_transfer.to_,
                            monitored=token_transfer.to_ in wallets_monitored.keys(),
                            custom_name=wallets_monitored[token_transfer.to_] if token_transfer.to_ in wallets_monitored else None
                        ),
                        amount=float_to_str(int(token_transfer.value, 16) * value_mult),
                        token_symbol=token_symbol,
                        token_address=token_transfer.contract_address
                    )
                )
        return ParsedNotification(chain_key=chain_key,
                                  user_id=user_id,
                                  tx_hash=transaction.hash,
                                  base_tran=base_tran,
                                  internal_transactions=internal_transactions,
                                  token_transfers=token_transfers)
