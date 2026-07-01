# flake8: noqa
"""
NVIDIA DGX Cloud Lepton API (v2) -- the public SDK surface.

This is the single, self-contained entry point for programmatically operating
the platform. Typical usage::

    from leptonai.api.v2 import APIClient

    client = APIClient()
    client.deployment.list_all()

Resource groups (``client.deployment``, ``client.job``, ``client.pod``,
``client.secret``, ``client.ingress``, ``client.storage``, ``client.log``,
``client.raycluster``, ``client.nodegroup``, ``client.template``) each expose
the operations for that resource. Data types live under
:mod:`leptonai.api.v2.types`.

Note that the web API is primarily intended for the ``lep`` CLI and the web
console; there is no SLA guarantee for high-frequency programmatic use.
"""

from .client import APIClient
from .workspace_record import WorkspaceRecord
from .api_resource import APIResourse, ClientError, ServerError
from .utils import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceUnauthorizedError,
    WorkspaceForbiddenError,
    WorkspaceNotCreatedYet,
    WorkspaceConfigurationError,
)
from . import types

__all__ = [
    "APIClient",
    "WorkspaceRecord",
    "APIResourse",
    "ClientError",
    "ServerError",
    "WorkspaceError",
    "WorkspaceNotFoundError",
    "WorkspaceUnauthorizedError",
    "WorkspaceForbiddenError",
    "WorkspaceNotCreatedYet",
    "WorkspaceConfigurationError",
    "types",
]
