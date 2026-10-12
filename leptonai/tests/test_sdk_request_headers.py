"""Deployment calls identify their SDK origin."""

import httpx
import pytest
import respx

from leptonai import Client


@pytest.mark.parametrize("stream", [False, True])
@respx.mock
def test_deployment_health_openapi_and_inference_are_sdk_requests(stream, monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    base = "https://deployment.example"
    respx.get(base + "/healthz").mock(return_value=httpx.Response(200, json={}))
    respx.get(base + "/openapi.json").mock(
        return_value=httpx.Response(200, json={"paths": {}})
    )
    respx.get(base + "/status").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    respx.post(base + "/run").mock(
        return_value=httpx.Response(200, json={"answer": "done"})
    )
    client = Client(base, token="token", stream=stream)
    headers = {"x-lepton-client": "cli", "X-Custom": "custom"}

    assert client._get_proper_res_content(client._get("status", headers=headers)) == {
        "ok": True
    }
    assert client._get_proper_res_content(
        client._post("run", json={}, headers=headers)
    ) == {"answer": "done"}
    assert headers == {"x-lepton-client": "cli", "X-Custom": "custom"}
    assert len(respx.calls) == 4
    for call in respx.calls:
        assert call.request.headers["X-Lepton-Client"] == "sdk"
        assert call.request.headers["Authorization"] == "Bearer token"
    for call in respx.calls[2:]:
        assert call.request.headers["X-Custom"] == "custom"
    client._session.close()
