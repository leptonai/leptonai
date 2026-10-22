"""Surface the server's explanation when workspace access is forbidden."""

import pytest
import responses

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.utils import WorkspaceForbiddenError


BASE = "https://gateway.example/api/v2/workspaces/ws"
CORPNET_ERROR = (
    "Access restricted to corpnet IPs only. Please connect from an authorized network."
)


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"json": {"error": CORPNET_ERROR}}, CORPNET_ERROR),
        ({"json": {"message": " denied "}}, "denied"),
        ({"json": {"code": "Permission Denied"}}, None),
        ({"json": ["not", "a", "dict"]}, None),
        ({"body": "<html>Forbidden</html>"}, None),
    ],
)
@responses.activate
def test_info_forbidden_carries_server_reason(kwargs, reason):
    responses.add(responses.GET, BASE + "/workspace", status=403, **kwargs)

    with pytest.raises(WorkspaceForbiddenError) as exc_info:
        APIClient("ws", "nvapi-test", BASE).info()

    assert exc_info.value.reason == reason
    if reason:
        assert f"Reason: {reason}" in str(exc_info.value)
