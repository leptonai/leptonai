# flake8: noqa
"""
Lepton API v1 is a cleaned up version of the API that interacts with the platform.
"""

from . import types
from . import client

import warnings as _warnings

_warnings.warn(
    "The v1 API is deprecated and will be removed in the next major version. Consider"
    " using the v2 API for new code.",
    DeprecationWarning,
    stacklevel=2,
)
