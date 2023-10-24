import asyncio
import inspect
import functools

import anyio
from loguru import logger


# Similar to starlette.background.BackgroundTask, but can accept
# custom limiter (we use it to control max concurrency)
class BackgroundTask:
    def __init__(self, func, *args, **kwargs):
        if inspect.iscoroutinefunction(func):
            raise ValueError("Background tasks cannot be async functions.")

        self.func = functools.partial(func, *args, **kwargs)

    async def __call__(self, semaphore):
        try:
            logger.debug(f"Running background task with {self.func}")
            async with semaphore:
                result = await anyio.to_thread.run_sync(self.func)
                return result
            logger.debug(f"Finished background task with {self.func}")
        except Exception as e:
            logger.exception(e)
