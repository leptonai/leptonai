from unittest.mock import patch

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.workspace_record import WorkspaceRecord


def test_client_allows_missing_optional_auth_token(monkeypatch):
    monkeypatch.delenv("LEPTON_WORKSPACE_TOKEN", raising=False)

    with patch.object(WorkspaceRecord, "has", return_value=False):
        client = APIClient(
            workspace_id="public-workspace",
            auth_token=None,
            url="https://api.example",
        )

    try:
        assert client.auth_token is None
        assert "Authorization" not in client._header
    finally:
        client._session.close()


def test_client_keeps_auth_token_masked_in_trace(monkeypatch):
    monkeypatch.delenv("LEPTON_WORKSPACE_TOKEN", raising=False)

    with (
        patch.object(WorkspaceRecord, "has", return_value=False),
        patch("leptonai.api.v2.client.logger.trace") as trace,
    ):
        client = APIClient(
            workspace_id="private-workspace",
            auth_token="secret-token",
            url="https://api.example",
        )

    try:
        message = trace.call_args.args[0]
        assert "se****en" in message
        assert "secret-token" not in message
    finally:
        client._session.close()
