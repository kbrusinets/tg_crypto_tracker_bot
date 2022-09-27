from typing import List, Optional

from pydantic.main import BaseModel


class TokenTransferInfo(BaseModel):
    transaction_hash: str
    contract_address: str
    from_: str
    to_: str
    value: str


class InternalTransactionInfo(BaseModel):
    from_: str
    to_: Optional[str]
    value: str


class TransactionInfo(BaseModel):
    hash: str
    from_: str
    to_: Optional[str]
    value: str
    timestamp: int
    token_transfers: List[TokenTransferInfo] = []
    internal_transactions: List[InternalTransactionInfo] = []


class NewTransactionsNotification(BaseModel):
    chain_key: str
    transactions: List[TransactionInfo]


class ParsedWallet(BaseModel):
    address: str
    monitored: bool
    custom_name: Optional[str]


class ParsedCoinTransfer(BaseModel):
    from_: ParsedWallet
    to_: ParsedWallet
    amount: str


class ParsedTokenTransfer(BaseModel):
    from_: ParsedWallet
    to_: ParsedWallet
    amount: str
    token_symbol: str
    token_address: str


class WalletAddToTrack(BaseModel):
    address: str
    reason: str


class ParsedNotification(BaseModel):
    chain_key: str
    timestamp: int
    user_id: int
    tx_hash: str
    base_tran: Optional[ParsedCoinTransfer]
    internal_transactions: List[ParsedCoinTransfer] = []
    token_transfers: List[ParsedTokenTransfer] = []
    autoadded_wallets: List[WalletAddToTrack] = []
    wallets_to_ask: List[WalletAddToTrack] = []
