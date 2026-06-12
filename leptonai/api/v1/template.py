"""v1.template is a thin shim that re-exports the v2 implementation.

Keeping this file allows ``import leptonai.api.v1.template`` code to work
while the real logic lives in ``leptonai.api.v2.template``.
"""

from ..v2.template import TemplateAPI  # re-export

__all__ = ["TemplateAPI"]
