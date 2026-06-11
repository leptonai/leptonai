# flake8: noqa
"""
The old v0 api that is going to be deprecated. Make sure you use v1 for new code.
"""
import warnings

from . import connection
from . import deployment
from . import job
from . import nodegroup
from . import secret
from . import storage
from . import types
from . import util
from . import workspace


warnings.warn(
    "The v0 API is deprecated and will be removed in the next major version. Consider"
    " using the v1 API for new code.",
    DeprecationWarning,
    stacklevel=2,
)
