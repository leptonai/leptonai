import inspect
import functools

import anyio
from loguru import logger


def create_limiter(max_concurrency):
    return anyio.CapacityLimiter(total_tokens=max_concurrency)


# Similar to starlette.background.BackgroundTask, but can accept
# custom limiter (we use it to control max concurrency)
class BackgroundTask:
    def __init__(self, func, *args, **kwargs):
        if inspect.iscoroutinefunction(func):
            raise ValueError("Background tasks cannot be async functions.")
        self.func = functools.partial(func, *args, **kwargs)

    async def __call__(self, limiter=None):
        try:
            return await anyio.to_thread.run_sync(self.func, limiter=limiter)
        except Exception as e:
            logger.exception(e)
