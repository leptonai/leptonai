"""
Lepton SDK for Python.
"""
from . import photon  # noqa: F401
from .client import Client  # noqa: F401
from ._version import __version__  # noqa: F401

# importing `_internal.logging` triggers the setup of
# attaching a log file handler to the logger
from ._internal import logging as _internal_logging

del _internal_logging
