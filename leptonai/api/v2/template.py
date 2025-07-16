from typing import Any, Dict

from ..v1.api_resource import APIResourse


class TemplateAPI(APIResourse):
    """API for rendering workspace templates (v2).

    Endpoint:
        POST /templates/public/{template_id}/render
    """

    def render(self, template_id: str, payload: Dict[str, Any]) -> Any:  # noqa: ANN401
        response = self._post(f"/templates/public/{template_id}/render", json=payload)
        return self.ensure_type(response, LeptonJob) 