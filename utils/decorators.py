import asyncio
from asyncio import TimeoutError
import traceback

from aiohttp import ClientConnectionError, ContentTypeError, ClientResponseError
from datetime import datetime


def http_exception_handler(fun):
    async def try_to_run(*args, **kwargs):
        retries = 5
        while True:
            try:
                return await fun(*args, **kwargs)
            except (ClientConnectionError, TimeoutError):
                print(f'{datetime.now()} Connection error while requesting {fun.__name__ }. Trying again.')
                await asyncio.sleep(2)
            except (ContentTypeError, ClientResponseError) as e:
                print(f'{datetime.now()} Wrong response while requesting {fun.__name__}. Trying again.')
                print(f'{datetime.now()} {e}')
                await asyncio.sleep(2)
            except Exception as error:
                print(f'{datetime.now()} Unexpected error while requesting {fun.__name__ }. Trying again.')
                print(f'{datetime.now()} {traceback.format_exc()}')
                await asyncio.sleep(2)
            if retries > 0:
                print(f'{datetime.now()} Trying again.')
                await asyncio.sleep(2)
                retries -= 1
            else:
                print(f'{datetime.now()} Skipping.')
                return None

    return try_to_run
