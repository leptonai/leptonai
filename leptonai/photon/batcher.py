import anyio
import asyncio
from asyncio import Future, Queue, Task, TimeoutError, wait_for
from functools import wraps
import time
from typing import List, Optional
from uuid import uuid4

from leptonai.util import asyncfy_with_semaphore


def batch(
    max_batch_size: int,
    max_wait_time: float,
    semaphore: Optional[anyio.Semaphore] = None,
    timeout: Optional[float] = None,
):
    """Decorator that batches calls to a function

    Args:
        max_batch_size (int): Maximum number of calls to batch together
        max_wait_time (float): Maximum time (in seconds) to wait before
            executing a batch
        semaphore (anyio.Semaphore): Semaphore to use for concurrency control. If func
            is already async, this argument is ignored. If func is sync, it will be
            guarded by the semaphore.
    """

    if max_batch_size <= 1:
        raise ValueError("max_batch_size should be greater than 1")
    if max_wait_time <= 0:
        raise ValueError("max_wait_time should be greater than 0")

    def decorator(func):
        func = asyncfy_with_semaphore(func, semaphore=semaphore, timeout=timeout)

        # list of (request_id, args, kwargs)
        # using list here is a hack to make it mutable inside closures
        _requests: List[Optional[Queue]] = [None]

        def get_requests_queue():
            if _requests[0] is None:
                _requests[0] = Queue(maxsize=max_batch_size)
            return _requests[0]

        # request_id -> result
        results = {}

        # running task - same to _requests, using list as a hack
        running_task: List[Optional[Task]] = [None]

        # run a coroutine with a callback. !!caller should keep a reference to
        # the returned task to avoid GC (asyncio loop only keeps a weakref to
        # the task)
        def schedule_task(co, cb) -> Task:
            task = asyncio.create_task(co)
            task.add_done_callback(cb)
            return task

        def create_future() -> Future:
            loop = asyncio.get_event_loop()
            return loop.create_future()

        async def batch_requests():
            while not get_requests_queue().empty():
                start_time = time.time()

                batch_request = []
                while len(batch_request) < max_batch_size:
                    if get_requests_queue().empty():
                        time_elapsed = time.time() - start_time
                        timeout = max_wait_time - time_elapsed
                        try:
                            request = await wait_for(
                                get_requests_queue().get(), timeout=timeout
                            )
                        except TimeoutError:
                            break
                    else:
                        request = await get_requests_queue().get()

                    request_id, args, kwargs = request
                    batch_request.append((request_id, args, kwargs))
                yield batch_request

        async def execute_batch(batch_request):
            _, first_args, first_kwargs = batch_request[0]
            batch_args = [[] for _ in first_args]
            batch_kwargs = {k: [] for k in first_kwargs.keys()}
            for _, args, kwargs in batch_request:
                # TODO: check if args and kwargs of all requests align
                for i, arg in enumerate(args):
                    batch_args[i].append(arg)
                for k, v in kwargs.items():
                    batch_kwargs[k].append(v)

            batch_result = await func(*batch_args, **batch_kwargs)
            return batch_result

        def create_batch_done(batch_request):
            def batch_done(task):
                exception = task.exception()
                if exception is not None:
                    for request_id, _, _ in batch_request:
                        result_fut = results[request_id]
                        result_fut.set_exception(exception)
                    return

                batch_result = task.result()
                for i, (request_id, _, _) in enumerate(batch_request):
                    result = batch_result[i]
                    result_fut = results[request_id]
                    result_fut.set_result(result)
                return

            return batch_done

        async def execute_batches():
            async for batch_request in batch_requests():
                schedule_task(
                    execute_batch(batch_request), create_batch_done(batch_request)
                )

        def batches_done(task):
            exception = task.exception()
            if exception is not None:
                raise exception
            return

        def execute_if_ready():
            if running_task[0] is None or running_task[0].done():
                running_task[0] = schedule_task(execute_batches(), batches_done)

        @wraps(func)
        async def batch_func(*args, **kwargs):
            request_id = uuid4()

            # put the request into request queue
            await get_requests_queue().put((request_id, args, kwargs))

            # check if we have enough requests or waited long enough to execute
            # a batch
            execute_if_ready()

            # wait for the result
            result_fut = create_future()
            results[request_id] = result_fut
            try:
                result = await result_fut
                return result
            finally:
                del results[request_id]

        return batch_func

    return decorator
