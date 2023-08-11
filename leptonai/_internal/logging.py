"""
Internal logging module for Lepton. logs are written to
"logs/internal.log" inside the lepton directory. Once enabled, logs
triggered by
  - regular `logger.{debug,info,warning,error}` call will be written
  to both the log file and printed to the console;
  - `leptonai._internal.logging.log` call will only be written to the
  log file but not printed to the console.
"""
import os

from loguru import logger

from ..config import LOGS_DIR

_LEVEL = "LEPTON_INTERNAL"
_LOGFILE_BASE = LOGS_DIR / "internal.log"
_HANDLER_ID = None

# no = 9 slighly smaller the loguru's default level 10
logger.level(name=_LEVEL, no=9)


def _configure():
    global _HANDLER_ID

    _HANDLER_ID = logger.add(
        _LOGFILE_BASE,
        level=_LEVEL,
        colorize=False,
        rotation="10 MB",  # each log file will be max 10 MB
        retention=3,  # max keep 3 log files
        compression="zip",  # compress the log files
    )


_enabled = False


def disable():
    global _enabled
    if _enabled:
        if _HANDLER_ID is not None:
            logger.remove(_HANDLER_ID)
        _enabled = False


def enable():
    global _enabled

    if os.environ.get("LEPTON_DISABLE_INTERNAL_LOG", "0").lower() in ("1", "true"):
        return

    if not _enabled:
        _configure()
        _enabled = True


def log(*args, **kwargs):
    if not _enabled:
        return
    return logger.opt(depth=1).log(_LEVEL, *args, **kwargs)


enable()
