"""Origin headers on SDK requests and CLI login."""

import os
import tempfile
from unittest.mock import patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
import responses
from click.testing import CliRunner

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.workspace_record import (
    LocalWorkspaceInfo,
    WorkspaceRecord,
    _LocalWorkspaceRecord,
)
from leptonai.cli import lep


BASE = "https://gateway.dgxc-lepton.nvidia.com/api/v2/workspaces/ws1"
ORIGIN = "https://gateway.dgxc-lepton.nvidia.com"
WORKSPACE_INFO = {
    "build_time": "today",
    "git_commit": "0.1.2",
    "workspace_name": "ws1",
    "workspace_tier": "basic",
    "workspace_state": "normal",
    "supported_shapes": {},
    "workspace_disk_usage_bytes": 0,
    "workloads": {
        "num_deployments": 0,
        "num_jobs": 0,
        "num_pods": 0,
        "num_secrets": 0,
        "num_image_pull_secrets": 0,
    },
    "resource_quota": {
        "limit": {"cpu": 0, "memory": 0, "accelerator_num": 0},
        "used": {"cpu": 0, "memory": 0, "accelerator_num": 0},
    },
}


@pytest.fixture(autouse=True)
def isolated_workspace(monkeypatch, tmp_path):
    for name in (
        "LEPTON_WORKSPACE_ID",
        "LEPTON_WORKSPACE_TOKEN",
        "LEPTON_WORKSPACE_URL",
        "LEPTON_WORKSPACE_ORIGIN_URL",
        "LEPTON_DEBUG_HEADERS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(WorkspaceRecord, "_singleton_record", _LocalWorkspaceRecord())
    monkeypatch.setattr(
        WorkspaceRecord, "WORKSPACE_FILE", tmp_path / "workspace_info.yaml"
    )


@pytest.mark.parametrize(
    "source, origin_url, expected",
    [
        ("default", None, ORIGIN),
        (
            "argument",
            "https://console.example:8443/api?x=1#section",
            "https://console.example:8443",
        ),
        ("environment", "http://localhost:8080/api/workspace", "http://localhost:8080"),
        ("record", BASE, ORIGIN),
        ("argument", "http://[::1]:8080/api", "http://[::1]:8080"),
    ],
)
@responses.activate
def test_workspace_request_origin(monkeypatch, source, origin_url, expected):
    kwargs = {}
    if source == "argument":
        kwargs["workspace_origin_url"] = origin_url
    elif source == "environment":
        monkeypatch.setenv("LEPTON_WORKSPACE_ORIGIN_URL", origin_url)
    elif source == "record":
        WorkspaceRecord._singleton_record.workspaces["ws1"] = LocalWorkspaceInfo(
            id="ws1", url=BASE, auth_token="token", workspace_origin_url=origin_url
        )

    responses.get(f"{BASE}/workspace", json=WORKSPACE_INFO)
    client = APIClient(workspace_id="ws1", auth_token="token", url=BASE, **kwargs)
    client.info()

    request = responses.calls[0].request
    assert request.url == f"{BASE}/workspace"
    assert request.headers["Origin"] == expected
    assert request.headers["Authorization"] == "Bearer token"
    assert client.workspace_origin_url == expected


@responses.activate
def test_classic_workspace_has_no_default_origin():
    url = "https://classic.example/api/v1"
    responses.get(f"{url}/workspace", json=WORKSPACE_INFO)

    APIClient(workspace_id="ws1", auth_token="token", url=url).info()

    assert "Origin" not in responses.calls[0].request.headers


@pytest.mark.parametrize(
    "command",
    [
        ["login", "-c", "ws1:token"],
        ["workspace", "login", "-i", "ws1", "-t", "token"],
    ],
)
@pytest.mark.parametrize("explicit_origin", [False, True])
@responses.activate
def test_login_sends_and_saves_origin_without_path(command, explicit_origin):
    responses.get(f"{BASE}/workspace", json=WORKSPACE_INFO)
    responses.get(BASE, json={"display_name": "ws1"})
    responses.get(f"{BASE}/tokens", json=[])
    expected = ORIGIN
    if explicit_origin:
        command = command + [
            "--workspace-origin-url",
            "https://console.example:8443/login",
        ]
        expected = "https://console.example:8443"

    with patch("leptonai.cli.cli.check_lepton_version"):
        result = CliRunner().invoke(lep, command)

    assert result.exit_code == 0, result.output
    assert responses.calls[0].request.headers["Origin"] == expected
    WorkspaceRecord.reload()
    assert WorkspaceRecord.current().workspace_origin_url == expected
    assert WorkspaceRecord.current().url == BASE
