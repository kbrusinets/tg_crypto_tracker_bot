from async_lru import alru_cache
import time
from functools import wraps


def timed_lru(max_age):
    def _decorator(fn):
        @alru_cache()
        async def _new(*args, __time_salt, **kwargs):
            return await fn(*args, **kwargs)

        @wraps(fn)
        async def _wrapped(*args, **kwargs):
            return await _new(*args, **kwargs, __time_salt=int(time.time() / max_age))

        return _wrapped

    return _decorator