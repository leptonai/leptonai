from unittest.mock import patch

import responses

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.workspace_record import WorkspaceRecord


BASE_URL = "https://api.example"


def make_client():
    with patch.object(WorkspaceRecord, "has", return_value=False):
        return APIClient(
            workspace_id="workspace",
            auth_token="default-token",
            url=BASE_URL,
            workspace_origin_url="https://workspace.example",
        )


@responses.activate
def test_request_preserves_case_insensitive_header_overrides():
    client = make_client()
    responses.get(f"{BASE_URL}/resource", json={})

    try:
        client._get(
            "/resource",
            headers={
                "authorization": "Bearer override-token",
                "Origin": "https://override.example",
            },
        )

        request_headers = responses.calls[0].request.headers
        assert request_headers["Authorization"] == "Bearer override-token"
        assert request_headers["Origin"] == "https://override.example"
    finally:
        client._session.close()


@responses.activate
def test_request_adds_default_headers_to_custom_headers():
    client = make_client()
    responses.get(f"{BASE_URL}/resource", json={})

    try:
        client._get("/resource", headers={"X-Request-ID": "request-id"})

        request_headers = responses.calls[0].request.headers
        assert request_headers["Authorization"] == "Bearer default-token"
        assert request_headers["Origin"] == "https://workspace.example"
        assert request_headers["X-Request-ID"] == "request-id"
    finally:
        client._session.close()
