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
        self.func = func
        self.args = args
        self.kwargs = kwargs

    async def __call__(self, limiter=None):
        try:
            if inspect.iscoroutinefunction(self.func):
                return await self.func(*self.args, **self.kwargs)
            else:
                # anyio.to_thread.run_sync doesn't accept kwargs
                func = functools.partial(self.func, **self.kwargs)
                return await anyio.to_thread.run_sync(func, *self.args, limiter=limiter)
        except Exception as e:
            logger.exception(e)
