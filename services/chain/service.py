import re
from typing import List, AsyncGenerator, Dict, Optional

from web3.contract import Contract

from schemas import NewTransactionsNotification
from services.chain.chain_interface import ChainInterface
from aiostream.stream import merge as aiomerge

from services.db.schemas import ChainSchema


class ChainsService:
    def __init__(self, chains: List[ChainInterface]):
        chain_key_regex = re.compile('^[_a-zA-Z0-9]*$')
        for chain in chains:
            if not chain_key_regex.match(chain.chain_key):
                raise ValueError(f'Wrong chain key name - {chain.chain_key}. Please use only letters, digits and underscore.')
            self.chains = {
            chain.chain_key: chain for chain in chains
        }

    async def monitor(self) -> AsyncGenerator[NewTransactionsNotification, None]:
        for chain in self.chains.values():
            await chain.start()
        async for notif in aiomerge(*[self.monitor_chain(chain) for chain in self.chains.values()]):
            yield notif

    async def monitor_chain(self, chain) -> AsyncGenerator[NewTransactionsNotification, None]:
        async for new_transactions in chain.subscribe_to_new_transactions():
            notification = NewTransactionsNotification(
                chain_key=chain.chain_key,
                transactions=list(new_transactions.values())
            )
            yield notification

    async def get_contract(self, chain_key: str, address: str) -> Contract:
        return await self.chains[chain_key].get_contract(address=address)

    async def get_transaction_receipt(self, chain_key: str, tx_hash: str) -> Dict:
        return await self.chains[chain_key].get_transaction_receipt(tx_hash=tx_hash)

    async def get_amount_of_normal_transactions(self, chain_key: str, address: str) -> int:
        return await self.chains[chain_key].get_amount_of_normal_transactions(address=address)

    async def get_amount_of_token_transactions(self, chain_key: str, address: str) -> int:
        return await self.chains[chain_key].get_amount_of_token_transactions(address=address)

    async def get_wallet_scan_name(self, chain_key: str, address: str) -> int:
        return await self.chains[chain_key].get_wallet_scan_name(address=address)

    async def get_first_transaction_ts(self, chain_key: str, address: str) -> Optional[int]:
        return await self.chains[chain_key].get_first_transaction_ts(address=address)

    def get_scan_tx_link(self, chain_key: str, tx_hash: str) -> str:
        return self.chains[chain_key].get_scan_tx_link(tx_hash=tx_hash)

    def get_scan_wallet_link(self, chain_key: str, address: str) -> str:
        return self.chains[chain_key].get_scan_wallet_link(address=address)

    def get_chain_info(self, chain_key: str) -> ChainSchema:
        return ChainSchema(
            key=chain_key,
            name=self.chains[chain_key].chain_name,
            coin_symbol=self.chains[chain_key].chain_coin
        )

    def get_chains_keys(self) -> List[str]:
        return list(self.chains.keys())
