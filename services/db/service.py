from collections import defaultdict
from typing import List, Set, Dict, Optional

from sqlalchemy.exc import IntegrityError

from services.chain.chain_interface import ChainInterface
from services.db.crud import DbCrud
from services.db.models import Chain, TrackingMap, TrackingMapLog
from services.db.schemas import ChainSchema, TrackingMapSchema
from datetime import datetime as dt


class DbService:
    def __init__(self):
        self.crud = DbCrud()

    async def start(self, chains: List[ChainInterface]):
        await self.crud.start()
        for chain in chains:
            async with self.crud.get(Chain, key=chain.chain_key) as resp:
                found_chain = resp.first()
                if not found_chain:
                    existing = None
                else:
                    existing = ChainSchema.from_orm(found_chain[0])
            if existing is None:
                new_chain = Chain(key=chain.chain_key,
                                  name=chain.chain_name,
                                  coin_symbol=chain.chain_coin)
                async with self.crud.create(new_chain):
                    pass
            else:
                if existing.coin_symbol != chain.chain_coin or existing.name != chain.chain_name:
                    raise ValueError(f'Chains info in db and in config do not match. Chain key = {chain.chain_key}.'
                                     f'Db name = {existing.name}, config name = {chain.chain_name}.'
                                     f'Db coin = {existing.coin_symbol}, config coin = {chain.chain_coin}')

    async def check_who_tracks_wallets(self, chain_key: str, wallets_involved: Set[str]) -> Dict[int, Dict[str, str]]:
        wallets_involved = {wallet.lower() for wallet in wallets_involved}
        async with self.crud.get(TrackingMap, TrackingMap.wallet.in_(wallets_involved),
                               chain_key=chain_key) as result:
            results = result.all()
            trackings = defaultdict(dict)
            for tracking in results:
                trackings[tracking[0].user_id][tracking[0].wallet] = tracking[0].custom_name
            return trackings

    async def add_wallet_tracking(self, chain_key: str, user_id: int, wallet_address: str):
        try:
            new_tracking = TrackingMap(chain_key=chain_key, user_id=user_id, wallet=wallet_address.lower())
            async with self.crud.create(new_tracking):
                pass
            new_tracking_log = TrackingMapLog(
                chain_key=chain_key,
                user_id=user_id,
                wallet=wallet_address,
                start_date=dt.now()
            )
            async with self.crud.create(new_tracking_log):
                pass
            return True
        except IntegrityError:
            return False

    async def get_user_trackings(self, chain_key: str, user_id: int, wallet_address: str = None, custom_name: str = None):
        params = {
            'chain_key': chain_key,
            'user_id': user_id
        }
        if wallet_address:
            params['wallet'] = wallet_address.lower()
        if custom_name:
            params['custom_name'] = custom_name
        async with self.crud.get(TrackingMap, **params) as result:
            found_trackings =  result.all()
            if not found_trackings:
                return None
            return [TrackingMapSchema.from_orm(found_tracking[0]) for found_tracking in found_trackings]

    async def give_wallet_a_name(self, chain_key: str, user_id: int, wallet_address: str, wallet_name: str):
        wallet_address = wallet_address.lower()
        try:
            async with self.crud.update(TrackingMap, {'custom_name': wallet_name}, chain_key=chain_key, user_id=user_id, wallet=wallet_address):
                pass
            async with self.crud.update(TrackingMapLog, {'end_date': dt.now()}, chain_key=chain_key, user_id=user_id, wallet=wallet_address, end_date=None):
                pass
            new_tracking_log = TrackingMapLog(
                chain_key=chain_key,
                user_id=user_id,
                wallet=wallet_address,
                custom_name=wallet_name,
                start_date=dt.now()
            )
            async with self.crud.create(new_tracking_log):
                pass
            return True
        except IntegrityError:
            return False

    async def get_wallet_name(self, chain_key: str, user_id: int, wallet_address: str):
        async with self.crud.get(TrackingMap, chain_key=chain_key, user_id=user_id, wallet=wallet_address.lower()) as result:
            return result.first()[0].custom_name

    async def stop_wallet_tracking(self, chain_key: str, user_id: int, wallet_address: Optional[str] = None):
        params = {
            'chain_key': chain_key,
            'user_id': user_id
        }
        if wallet_address:
            params['wallet'] = wallet_address.lower()
        try:
            await self.crud.delete(TrackingMap, **params)
            async with self.crud.update(TrackingMapLog, {'end_date': dt.now()}, **params, end_date=None):
                pass
        except IntegrityError:
            return False

    async def get_native_coin(self, chain_key):
        async with self.crud.get(Chain, key=chain_key) as result:
            return result.first()[0].coin_symbol