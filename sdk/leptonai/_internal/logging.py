import os

from loguru import logger

from ..config import LOGS_DIR

_LEVEL = "LEPTON_INTERNAL"
_LOGFILE_BASE = LOGS_DIR / "internal.log"


def _configure():
    # allow disabling internal log by setting LEPTON_DISABLE_INTERNAL_LOG=1
    if os.environ.get("LEPTON_DISABLE_INTERNAL_LOG", "0").lower() in ("1", "true"):
        return

    # no = 9 slighly smaller the loguru's default level 10
    logger.level(name=_LEVEL, no=9)
    logger.add(
        _LOGFILE_BASE,
        level=_LEVEL,
        colorize=False,
        rotation="10 MB",  # each log file will be max 10 MB
        retention=3,  # max keep 3 log files
        compression="zip",  # compress the log files
    )


def log(*args, **kwargs):
    return logger.opt(depth=1).log(_LEVEL, *args, **kwargs)


_configure()
