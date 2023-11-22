"""
Implements the functionality to cancel a fastapi call when the client disconnects.
"""

import anyio
from exceptiongroup import catch, ExceptionGroup
from fastapi import Request, HTTPException
from loguru import logger


class ClientDisconnected(Exception):
    """
    Exception raised when the client disconnects.
    """

    pass


class TaskFinished(Exception):
    """
    Exception raised when the task finishes.
    """

    pass


async def _disconnect_poller(request: Request, interval: float):
    """
    Poll for disconnect. If the request disconnects, stop polling and return.
    """
    logger.trace("Starting disconnect poller")
    try:
        while True:
            await anyio.sleep(interval)
            if await request.is_disconnected():
                logger.trace(f"Request {request} disconnected.")
                raise ClientDisconnected()
    except anyio.get_cancelled_exc_class():
        logger.trace("Stopping disconnect poller")


async def run_with_cancel_on_disconnect(
    request: Request, cancel_on_connect_interval: float, callback, *args, **kwargs
):
    """
    Run the callback with the given arguments. If the client disconnects, cancel the callback.

    Args:
        request: The request object.
        cancel_on_connect_interval: The interval in seconds to poll for disconnect.
        callback: The callback to run.
        args: The arguments to pass to the callback.
        kwargs: The keyword arguments to pass to the callback.
    """
    result = []

    async def _callback_task_wrapper():
        logger.trace("Starting callback task wrapper")
        try:
            ret = await callback(*args, **kwargs)
            result.append(ret)
            raise TaskFinished()
        except anyio.get_cancelled_exc_class():
            # If the task is cancelled, do not raise anything.
            logger.trace("Callback task cancelled.")
        except TaskFinished:
            # If the task is finished, simply raise to finish execution.
            logger.trace("Callback task finished.")
            raise
        except Exception as e:
            # For any user code exceptions, we want to raise them and return.
            logger.trace(f"Callback task exception: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def handle_task_finished(e: ExceptionGroup) -> None:
        logger.trace("Task finished. Return normally.")
        if len(result) != 1:
            raise HTTPException(
                status_code=500,
                detail="You hit a programming error: callback returned >1 result.",
            )

    def handle_client_disconnected(e: ExceptionGroup) -> None:
        logger.trace("Client disconnected. Returning 503.")
        raise HTTPException(status_code=503, detail="Client disconnected.")

    def handle_http_exception(e: ExceptionGroup) -> None:
        logger.trace("HTTP exception. Reraise.")
        raise e.exceptions[0]

    with catch({
        TaskFinished: handle_task_finished,
        ClientDisconnected: handle_client_disconnected,
        HTTPException: handle_http_exception,
    }):  # type: ignore
        async with anyio.create_task_group() as tg:
            tg.start_soon(_disconnect_poller, request, cancel_on_connect_interval)
            tg.start_soon(_callback_task_wrapper)
    # If the above did not raise, we have a result.
    logger.info(f"Returning result: {result[0]}")
    return result[0]
