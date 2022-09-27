import asyncio

from aiohttp import ClientConnectionError
from datetime import datetime


def http_exception_handler(fun):
    async def try_to_run(*args, **kwargs):
        while True:
            try:
                return await fun(*args, **kwargs)
            except ClientConnectionError:
                print(f'{datetime.now()} Connection error while requesting {fun.__name__ }. Trying again.')
                await asyncio.sleep(2)

    return try_to_run
