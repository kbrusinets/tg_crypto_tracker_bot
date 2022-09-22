import asyncio
import json
import re
import uuid
from typing import Optional, Dict, AsyncGenerator, List

import aiohttp
from aiohttp import ContentTypeError
from websockets import connect
from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware
from bs4 import BeautifulSoup
from async_lru import alru_cache

from schemas import TransactionInfo, InternalTransactionInfo, TokenTransferInfo
from services.chain.chain_interface import ChainInterface
from utils.timed_lru_cache import timed_lru
from utils.utils import remove_trailing_zeros_from_address


class BSC(ChainInterface):

    _chain_key = 'BSC'
    _chain_name = 'Binance Smart Chain'
    _chain_coin = 'BNB'

    @property
    def chain_key(self):
        return self._chain_key

    @property
    def chain_name(self):
        return self._chain_name

    @property
    def chain_coin(self):
        return self._chain_coin

    def __init__(self):
        self.node_wss = 'wss://ws-nd-257-981-040.p2pify.com/f7250c4eea3433f6786ff3c2ea32bba4'
        self.node_http = 'https://nd-257-981-040.p2pify.com/f7250c4eea3433f6786ff3c2ea32bba4'
        self.scan_api_http = 'https://api.bscscan.com/api'
        self.scan_api_token = '5FQIDDZEC7HVXA861EN3ETK16XTW46ZX5Q'
        self.scan_url = 'https://bscscan.com'
        self.w3 = Web3(Web3.HTTPProvider(self.node_http))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.wss_connection = None
        self.http_session = None

    @alru_cache()
    async def get_contract(self, address: str) -> Optional[Contract]:
        params = {
            'module': 'contract',
            'action': 'getabi',
            'address': address,
            'apikey': self.scan_api_token
        }
        async with self.http_session.get(url=self.scan_api_http, params=params) as resp:
            abi = json.loads(await resp.text())
            if abi['status'] == '1':
                return self.w3.eth.contract(address=self.w3.toChecksumAddress(address), abi=abi['result'])
            else:
                return None

    @timed_lru(600)
    async def get_amount_of_normal_transactions(self, address: str) -> int:
        params = {
            'a': address
        }
        async with self.http_session.get(url='/'.join([self.scan_url.strip('/'), 'txs']), params=params) as resp:
            response = await resp.text()
            parsed = BeautifulSoup(response, 'html5lib')
            div_block = parsed.find("div", id="ContentPlaceHolder1_topPageDiv")
            if not div_block:
                return 0
            reg_search = '.*A total of ([\d,]*).*'
            str_amount = re.search(reg_search, div_block.p.span.text).group(1)
            return int(str_amount.replace(',', ''))

    @timed_lru(600)
    async def get_amount_of_token_transactions(self, address: str) -> int:
        params = {
            'a': address
        }
        async with self.http_session.get(url='/'.join([self.scan_url.strip('/'), 'tokentxns']), params=params) as resp:
            response = await resp.text()
            parsed = BeautifulSoup(response, 'html5lib')
            div_block = parsed.find("div", id="ContentPlaceHolder1_divTopPagination")
            if not div_block:
                return 0
            reg_search = '.*A total of ([\d,]*).*'
            str_amount = re.search(reg_search, div_block.p.text).group(1)
            return int(str_amount.replace(',', ''))

    @alru_cache()
    async def get_wallet_scan_name(self, address: str) -> Optional[str]:
        async with self.http_session.get(url='/'.join([self.scan_url.strip('/'), 'address', address])) as resp:
            response = await resp.text()
            parsed = BeautifulSoup(response, 'html5lib')
            tag = parsed.find('span', {'title': 'Public Name Tag (viewable by anyone)'})
            if tag:
                return tag.text
            else:
                return None

    async def get_first_transaction_ts(self, address: str) -> Optional[int]:
        normal_transactions = await self.get_normal_transactions(address=address, offset=1)
        token_transactions = await self.get_token_transactions(address=address, offset=1)
        values_to_compare = []
        if normal_transactions['status'] == '1':
            values_to_compare.append(int(normal_transactions['result'][0]['timeStamp']))
        if token_transactions['status'] == '1':
            values_to_compare.append(int(token_transactions['result'][0]['timeStamp']))
        if values_to_compare:
            return min(values_to_compare)
        else:
            return None

    def get_scan_tx_link(self, tx_hash: str) -> str:
        return '/'.join(s.strip('/') for s in (self.scan_url, 'tx', tx_hash))

    def get_scan_wallet_link(self, address: str) -> str:
        return '/'.join(s.strip('/') for s in (self.scan_url, 'address', address))

    async def start(self) -> None:
        self.wss_connection = await connect(self.node_wss)
        self.http_session = await aiohttp.ClientSession(headers={'Content-Type': 'application/json'}).__aenter__()

    async def websocket_consumer_handler(self) -> AsyncGenerator[Dict, None]:
        while True:
            message = await self.wss_connection.recv()
            yield json.loads(message)

    async def subscribe_to_new_blocks(self) -> None:
        json_rpc_id = str(uuid.uuid4())
        body = {
            "id": json_rpc_id,
            "method": "eth_subscribe",
            "params": ["newHeads"]
        }
        await self.wss_connection.send(json.dumps(body))

    def process_token_transfer_logs(self, transfer_logs: List[Dict]) -> List[TokenTransferInfo]:
        result = []
        for log in transfer_logs:
            values = [remove_trailing_zeros_from_address(topic) for topic in log['topics'][1:]]
            data = log['data'].removeprefix('0x')
            param_size_in_data = 64
            params_in_data = [data[i:i + param_size_in_data] for i in range(0, len(data), param_size_in_data)]
            values += [remove_trailing_zeros_from_address(param_in_data) for param_in_data in params_in_data]
            if len(values) == 3:
                result.append(TokenTransferInfo(
                    transaction_hash=log['transactionHash'],
                    contract_address=log['address'],
                    from_=values[0],
                    to_=values[1],
                    value=values[2]
                ))
            else:
                print(
                    f'Error while parsing transfer event for contract in log {int(log["logIndex"], 16)} in transaction {log["transactionHash"]}. Parsed parameters length = {len(values)}')
        return result

    async def subscribe_to_new_transactions(self) -> AsyncGenerator[Dict[str, TransactionInfo], None]:
        await self.subscribe_to_new_blocks()
        async for notification in self.websocket_consumer_handler():
            if 'method' in notification:
                new_block_number = notification["params"]["result"]["number"]
                print(f"New block: {new_block_number}")
                new_block_info = await self.get_block_by_number(block_number=new_block_number)
                transfer_topic = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
                block_transfer_logs = await self.get_logs(block_number=new_block_number, topics=[transfer_topic])
                internal_transactions = await self.get_internal_transactions(block_number=new_block_number)
                transactions = {}
                for transaction in new_block_info['result']['transactions']:
                    transactions[transaction['hash']] = TransactionInfo(
                        hash=transaction['hash'],
                        from_=transaction['from'],
                        to_=transaction['to'],
                        value=transaction['value']
                    )
                if internal_transactions['status'] == '1':
                    for int_tran in internal_transactions['result']:
                        transactions[int_tran['hash']].internal_transactions.append(
                            InternalTransactionInfo(
                                from_=int_tran['from'],
                                to_=int_tran['to'],
                                value=int_tran['value']
                            )
                        )
                for transfer in self.process_token_transfer_logs(transfer_logs=block_transfer_logs['result']):
                    transactions[transfer.transaction_hash].token_transfers.append(transfer)
                yield transactions

    async def get_block_by_number(self, block_number: str) -> Dict:
        data = {
            "id": str(uuid.uuid4()),
            "method": "eth_getBlockByNumber",
            "params": [block_number, True]
        }
        #TODO: Иногда бывает, что хттп апи запаздывает за вебсокетом и не возвращает блок, нотифицированный вебсокетом
        #TODO: Поэтому поставил здесь на этот случай повтор запроса
        for _ in range(0, 5):
            async with self.http_session.post(url=self.node_http, data=json.dumps(data)) as resp:
                try:
                    result = await resp.json()
                except ContentTypeError:
                    print('Content error in new block.')
                    await asyncio.sleep(1)
                    continue
            if result['result'] is None:
                print('sleeeping')
                await asyncio.sleep(1)
                print('woke up')
            else:
                break
        if result['result'] is None:
            raise ValueError(f'Block result still None. {block_number}')
        return result

    async def get_logs(self, block_number: str, topics: List[str]) -> Dict:
        data = {
            "id": str(uuid.uuid4()),
            "method": "eth_getLogs",
            "jsonrpc": "2.0",
            "params": [
                {
                    "fromBlock": block_number,
                    "toBlock": block_number,
                    "topics": topics
                }
            ]
        }
        async with self.http_session.post(url=self.node_http, data=json.dumps(data)) as resp:
            answer = await resp.json()
            return answer

    async def get_transaction_receipt(self, tx_hash: str) -> Dict:
        data = {
            "id": str(uuid.uuid4()),
            "method": "eth_getTransactionReceipt",
            "jsonrpc": "2.0",
            "params": [tx_hash]
        }
        async with self.http_session.post(url=self.node_http, data=json.dumps(data)) as resp:
            return await resp.json()

    async def get_internal_transactions(self, block_number: str) -> Dict:
        block_number = int(block_number, 16)
        params = {
            'module': 'account',
            'action': 'txlistinternal',
            'startblock': block_number,
            'endblock': block_number,
            'page': 1,
            'offset': 100,
            'sort': 'asc',
            'apikey': self.scan_api_token
        }
        async with self.http_session.get(url=self.scan_api_http, params=params) as resp:
            return await resp.json()

    async def get_normal_transactions(self,
                                      address: str,
                                      start_block: int = 0,
                                      end_block: int = 99999999,
                                      page: int = 1,
                                      offset: int = 100,
                                      sort_order: str = 'asc') -> Dict:
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': start_block,
            'endblock': end_block,
            'page': page,
            'offset': offset,
            'sort': sort_order,
            'apikey': self.scan_api_token
        }
        async with self.http_session.get(url=self.scan_api_http, params=params) as resp:
            return await resp.json()

    async def get_token_transactions(self,
                                     address: str,
                                     contract_address: str = None,
                                     page: int = 1,
                                     offset: int = 100,
                                     sort_order: str = 'asc') -> Dict:
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'page': page,
            'offset': offset,
            'sort': sort_order,
            'apikey': self.scan_api_token
        }
        if contract_address:
            params['contractaddress'] = contract_address
        async with self.http_session.get(url=self.scan_api_http, params=params) as resp:
            return await resp.json()