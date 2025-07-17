from typing import Any, Dict

from ..v1.api_resource import APIResourse
from ..v1.types.job import LeptonJob


class TemplateAPI(APIResourse):
    """API for rendering workspace templates (v2).

    Endpoint:
        POST /templates/public/{template_id}/render
    """

    def render(self, template_id: str, payload: Dict[str, Any]) -> LeptonJob:
        """Render template and return a LeptonJob object."""
        response = self._post(f"/templates/public/{template_id}/render", json=payload)
        return self.ensure_type(response, LeptonJob)
