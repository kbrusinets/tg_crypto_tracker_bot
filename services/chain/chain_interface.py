from abc import ABC, abstractmethod
from typing import Dict, Optional

from web3.contract import Contract


class ChainInterface(ABC):
    @property
    @abstractmethod
    def chain_key(self):
        pass

    @property
    @abstractmethod
    def chain_name(self):
        pass

    @property
    @abstractmethod
    def chain_coin(self):
        pass

    @abstractmethod
    async def get_contract(self, address: str) -> Optional[Contract]:
        pass

    @abstractmethod
    async def get_transaction_receipt(self, address: str) -> Dict:
        pass

    @abstractmethod
    async def get_amount_of_normal_transactions(self, address: str) -> int:
        pass

    @abstractmethod
    async def get_amount_of_token_transactions(self, address: str) -> int:
        pass

    @abstractmethod
    async def get_wallet_scan_name(self, address: str) -> Optional[str]:
        pass

    @abstractmethod
    async def get_first_transaction_ts(self, address: str) -> Optional[int]:
        pass

    @abstractmethod
    def get_scan_tx_link(self, tx_hash: str) -> str:
        pass

    @abstractmethod
    def get_scan_wallet_link(self, address: str) -> str:
        pass
