from typing import List, Optional
from pydantic import BaseModel


class LeptonWorkspaceTokenAuth(BaseModel):
    remove_authorization_header: Optional[bool] = None


class AuthConfig(BaseModel):
    lepton_workspace_token_auth: Optional[LeptonWorkspaceTokenAuth] = None
    ip_allowlist: Optional[List[str]] = None
