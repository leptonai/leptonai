"""v1.template is a thin shim that re-exports the v2 implementation.

Keeping this file allows ``import leptonai.api.v1.template`` code to work
while the real logic lives in ``leptonai.api.v2.template``.

Users on Lepton Classic won’t be able to call this API, but we keep it
here to minimize divergence between v1 and v2.
"""

from ..v2.template import TemplateAPI  # re-export

__all__ = ["TemplateAPI"]
