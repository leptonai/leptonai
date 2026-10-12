"""Identify SDK and CLI traffic at the HTTP and WebSocket boundaries."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import pytest
import responses
from click.testing import CliRunner

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.workspace_record import WorkspaceRecord, _LocalWorkspaceRecord
from leptonai.cli import lep


BASE = "https://gateway.example/api/v2/workspaces/ws"
WORKSPACE_INFO = {
    "build_time": "today",
    "git_commit": "0.1.2",
    "workspace_name": "ws",
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


def client(source):
    if source == "cli":
        from leptonai.cli.client import APIClient as CLIClient

        client_class = CLIClient
    else:
        client_class = APIClient
    return client_class(workspace_id="ws", auth_token="token", url=BASE)


@pytest.mark.parametrize("source", ["sdk", "cli"])
@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head"])
@pytest.mark.parametrize("custom_headers", [False, True])
@responses.activate
def test_every_http_method_retains_client_source(source, method, custom_headers):
    responses.add(method.upper(), BASE + "/resource", body="payload")
    headers = {
        "Content-Type": "application/octet-stream",
        "authorization": "Bearer custom",
        "x-lepton-client": "spoofed",
    }
    original_headers = headers.copy()
    kwargs = {"headers": headers} if custom_headers else {}

    response = getattr(client(source), "_" + method)("/resource", stream=True, **kwargs)
    response.close()

    request_headers = responses.calls[0].request.headers
    assert request_headers["X-Lepton-Client"] == source
    assert request_headers["Authorization"] == (
        "Bearer custom" if custom_headers else "Bearer token"
    )
    if custom_headers:
        assert request_headers["Content-Type"] == "application/octet-stream"
    assert headers == original_headers


@pytest.mark.parametrize(
    "command",
    [
        ["login", "-c", "ws:token"],
        ["workspace", "login", "-i", "ws", "-t", "token"],
    ],
)
@responses.activate
def test_cli_login_labels_validation_and_workspace_helpers(command):
    responses.get(BASE + "/workspace", json=WORKSPACE_INFO)
    responses.get(BASE, json={"display_name": "Workspace"})
    responses.get(BASE + "/tokens", json=[])

    with patch("leptonai.cli.cli.check_lepton_version"):
        result = CliRunner().invoke(lep, command + ["--workspace-url", BASE])

    assert result.exit_code == 0, result.output
    assert {call.request.url for call in responses.calls} == {
        BASE,
        BASE + "/workspace",
        BASE + "/tokens",
    }
    assert all(
        call.request.headers["X-Lepton-Client"] == "cli" for call in responses.calls
    )

    # A CLI invocation and its saved workspace must not change SDK defaults.
    WorkspaceRecord.client().info()
    assert responses.calls[-1].request.headers["X-Lepton-Client"] == "sdk"


@pytest.mark.parametrize("source", ["sdk", "cli"])
@responses.activate
def test_workspace_record_propagates_source_to_helper_requests(source):
    responses.get(BASE, json={"display_name": "Workspace"})
    responses.get(BASE + "/tokens", json=[])
    responses.get(BASE + "/workspace", json=WORKSPACE_INFO)
    kwargs = {"client_type": source} if source == "cli" else {}

    WorkspaceRecord.set("ws", "token", BASE, **kwargs)
    WorkspaceRecord.refresh_token_expires_at(**kwargs)
    WorkspaceRecord.client(**kwargs).info()

    assert [call.request.url for call in responses.calls] == [
        BASE,
        BASE + "/tokens",
        BASE + "/tokens",
        BASE + "/workspace",
    ]
    assert all(
        call.request.headers["X-Lepton-Client"] == source for call in responses.calls
    )


@responses.activate
def test_cli_log_workers_keep_source_and_do_not_pollute_sdk(monkeypatch):
    from leptonai.cli.log import _fetch_log_unit

    monkeypatch.setenv("LEPTON_WORKSPACE_ID", "ws")
    monkeypatch.setenv("LEPTON_WORKSPACE_TOKEN", "token")
    monkeypatch.setenv("LEPTON_WORKSPACE_URL", BASE)
    responses.get(BASE + "/logs", json={"data": {"result": []}})
    responses.get(BASE + "/sdk", json={})

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_fetch_log_unit, None, "job", None, None, "", 1, 10)
            for _ in range(3)
        ]
        for future in futures:
            assert not future.result(timeout=5).failed
        assert executor.submit(APIClient()._get, "/sdk").result(timeout=5).ok

    assert len(responses.calls) == 4
    for call in responses.calls:
        expected = "sdk" if call.request.url == BASE + "/sdk" else "cli"
        assert call.request.headers["X-Lepton-Client"] == expected


@pytest.mark.parametrize("source", ["sdk", "cli"])
def test_shell_handshake_keeps_client_source(source, monkeypatch):
    connect = Mock(return_value=Mock())
    monkeypatch.setattr("websocket.create_connection", connect)

    client(source).job.shell_connection("job", "job-0")

    assert connect.call_args.kwargs["header"]["X-Lepton-Client"] == source
    assert connect.call_args.kwargs["header"]["Authorization"] == "Bearer token"


@responses.activate
def test_cli_version_check_labels_its_request(monkeypatch, tmp_path):
    from leptonai.cli.cli import check_lepton_version

    monkeypatch.setattr("leptonai.config.VERSION_CHECK_FILE", tmp_path / "version")
    responses.get(
        "https://pypi.org/pypi/leptonai/json", json={"info": {"version": "0.0.0"}}
    )

    check_lepton_version()

    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["X-Lepton-Client"] == "cli"
