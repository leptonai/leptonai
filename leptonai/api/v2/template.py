from typing import Any, Dict, Optional

from leptonai.api.v1.types.deployment import LeptonDeployment

from ..v1.api_resource import APIResourse
from ..v1.types.job import LeptonJob
from .types.template import LeptonTemplate


class TemplateAPI(APIResourse):
    """API for rendering workspace templates (v2).

    Endpoints:
        POST   /templates/{public|private}/{template_id}/render
        GET    /templates/public
        GET    /templates/public/{template_id}
        GET    /templates/private
    """

    def render(
        self,
        template_id: str,
        payload: Dict[str, Any],
        is_private: Optional[bool] = None,
        is_pod: Optional[bool] = None,
    ) -> LeptonJob:
        """Render a template.

        Logic (simple and efficient):
        - If is_private is True/False: use that namespace directly.
        - If is_private is None: list public, check by id only; if found -> public,
          otherwise render from private (without extra listing).
        """

        if is_private is None:
            pubs = self.list_public()
            in_public = any(t.metadata and t.metadata.id_ == template_id for t in pubs)
            ns = "public" if in_public else "private"
        else:
            ns = "private" if is_private else "public"

        response = self._post(f"/templates/{ns}/{template_id}/render", json=payload)
        if is_pod:
            return self.ensure_type(response, LeptonDeployment)
        return self.ensure_type(response, LeptonJob)

    # Lists
    def list_public(self) -> Any:
        response = self._get("/templates/public")
        return self.ensure_list(response, LeptonTemplate)

    def list_private(self) -> Any:
        response = self._get("/templates/private")
        return self.ensure_list(response, LeptonTemplate)

    # Gets
    def get_public(self, template_id: str) -> LeptonTemplate:
        response = self._get(f"/templates/public/{template_id}")
        return self.ensure_type(response, LeptonTemplate)

    def get_private(self, template_id: str) -> LeptonTemplate:
        response = self._get(f"/templates/private/{template_id}")
        return self.ensure_type(response, LeptonTemplate)
