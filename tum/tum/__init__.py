from loguru import logger
import torch

from . import _tum
from ._tum import is_current_allocator_initialized, prefetch, metadata  # noqa: F401

try:
    from torch.cuda.memory import CUDAPluggableAllocator  # noqa: F401
except ImportError:
    raise RuntimeError(
        "Your torch version is too old. Please upgrade to v2.0.0 or higher."
    )


_tum_allocator = None


def get_tum_allocator():
    global _tum_allocator
    if _tum_allocator is None:
        _tum_allocator = torch.cuda.memory.CUDAPluggableAllocator(
            _tum.__file__, "tum_malloc", "tum_free"
        )
    return _tum_allocator


enabled = False


def enable():
    global enabled
    if enabled:
        return

    if is_current_allocator_initialized():
        logger.error(
            "Can not switch to TUM allocator because existing allocator is already"
            " initialized. You need to call `tum.enable()` earlier."
        )
        return
    logger.info("Enabling TUM allocator")
    alloc = get_tum_allocator()
    torch.cuda.memory.change_current_allocator(alloc)
    enabled = True
