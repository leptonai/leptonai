# flake8: noqa
"""
Bootstrap for API v2.

This module provides a shallow re-export of v1 resources, so users can migrate to
leptonai.api.v2 import paths without behavior changes. Modules that already have
native v2 implementations should be imported from v2 directly and are not
re-exported here.
"""

# Native v2 modules (keep as-is, do not re-export from v1)
from .client import APIClient  # noqa: F401
from .resource_shape import ResourceShapeAPI  # noqa: F401
from .template import TemplateAPI  # noqa: F401
from .dedicated_node_groups import DedicatedNodeGroupAPI  # noqa: F401
from .utils import *  # noqa: F401,F403
from .workspace_record import WorkspaceRecord  # noqa: F401

# Shallow re-exports from v1 (until their native v2 versions are implemented)
from ..v1.deployment import DeploymentAPI  # noqa: F401
from ..v1.job import JobAPI  # noqa: F401
from ..v1.secret import SecretAPI  # noqa: F401
from ..v1.kv import KVAPI  # noqa: F401
from ..v1.queue import QueueAPI  # noqa: F401
from ..v1.pod import PodAPI  # noqa: F401
from ..v1.ingress import IngressAPI  # noqa: F401
from ..v1.storage import StorageAPI  # noqa: F401
from ..v1.object_storage import ObjectStorageAPI  # noqa: F401
from ..v1.log import LogAPI  # noqa: F401
from ..v1.raycluster import RayClusterAPI  # noqa: F401

# types remain in v1 for now; import selectively when needed in modules
