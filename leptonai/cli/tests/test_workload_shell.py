"""Workspace-API shells for pods, endpoints, jobs and Ray clusters."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import websocket
from click.testing import CliRunner

from leptonai.api.v2.shell import ShellUnavailable
from leptonai.cli import lep


SOCKET = object()


def _text(result):
    # Rich wraps console output at 80 columns under CliRunner.
    return " ".join(result.output.split())


def _api():
    api = Mock()
    api.get_shell_replica.return_value = "replica-0"
    api.shell_connection.return_value = SOCKET
    return api


def _client():
    # One API double per workload, so a command calling the wrong one fails.
    job = _api()
    job.list_all.return_value = [
        SimpleNamespace(metadata=SimpleNamespace(name="train", id_="train-id")),
        SimpleNamespace(metadata=SimpleNamespace(name="train-2", id_="other")),
    ]
    return SimpleNamespace(
        pod=_api(), deployment=_api(), raycluster=_api(), job=job, workspace_id="ws"
    )


def _apis(client):
    return {
        "pod": client.pod,
        "endpoint": client.deployment,
        "job": client.job,
        "raycluster": client.raycluster,
    }


COMMANDS = {
    "pod": ("leptonai.cli.pod.APIClient", ["pod", "shell", "-n", "my-pod"]),
    "endpoint": (
        "leptonai.cli.deployment.APIClient",
        ["endpoint", "shell", "-n", "my-ep"],
    ),
    "job": ("leptonai.cli.job.APIClient", ["job", "shell", "--id", "train-id"]),
    "raycluster": (
        "leptonai.cli.raycluster.APIClient",
        ["raycluster", "shell", "-n", "my-rc"],
    ),
}


def _invoke(kind, *extra, client=None, exit_code=0):
    target, args = COMMANDS[kind]
    client = client or _client()
    with (
        patch(target, return_value=client),
        patch("leptonai.cli.ws_shell.ensure_interactive_terminal"),
        patch("leptonai.cli.ws_shell.run_ws_shell", return_value=exit_code) as bridge,
    ):
        result = CliRunner().invoke(lep, [*args, *extra])
    return result, client, bridge


@pytest.mark.parametrize("kind", sorted(COMMANDS))
def test_shell_selects_a_replica_and_bridges_the_socket(kind):
    result, client, bridge = _invoke(kind, "--replica", "replica-0")
    assert result.exit_code == 0, result.output
    name = {"pod": "my-pod", "endpoint": "my-ep", "job": "train-id"}.get(kind, "my-rc")
    for other, api in _apis(client).items():
        if other == kind:
            api.get_shell_replica.assert_called_once_with(name, "replica-0")
            api.shell_connection.assert_called_once_with(name, "replica-0")
        else:
            api.get_shell_replica.assert_not_called()
            api.shell_connection.assert_not_called()
    bridge.assert_called_once_with(SOCKET)
    assert "type `exit` or press Ctrl-D to leave" in _text(result)


@pytest.mark.parametrize("kind", sorted(COMMANDS))
def test_shell_exit_code_is_the_remote_exit_code(kind):
    result, _, _ = _invoke(kind, exit_code=130)
    assert result.exit_code == 130


def test_ray_cluster_shell_opens_on_the_head_by_default():
    client = _client()
    client.raycluster.get_shell_replica.return_value = None
    result, _, _ = _invoke("raycluster", client=client)
    assert result.exit_code == 0, result.output
    assert "the head node of Ray cluster my-rc" in _text(result)
    client.raycluster.shell_connection.assert_called_once_with("my-rc", None)


def test_job_shell_resolves_an_exact_live_job_name():
    target, _ = COMMANDS["job"]
    client = _client()
    with (
        patch(target, return_value=client),
        patch("leptonai.cli.ws_shell.ensure_interactive_terminal"),
        patch("leptonai.cli.ws_shell.run_ws_shell", return_value=0),
    ):
        result = CliRunner().invoke(lep, ["job", "shell", "--name", "train"])
        assert result.exit_code == 0, result.output
        client.job.get_shell_replica.assert_called_once_with("train-id", None)

        ambiguous = CliRunner().invoke(lep, ["job", "shell", "--id", "a", "-n", "b"])
        assert ambiguous.exit_code == 2


@pytest.mark.parametrize("kind", sorted(COMMANDS))
def test_unavailable_shell_targets_fail_before_dialling(kind):
    client = _client()
    api = _apis(client)[kind]
    api.get_shell_replica.side_effect = ShellUnavailable("It has no running replicas.")
    result, _, bridge = _invoke(kind, client=client)
    assert result.exit_code == 1
    assert "has no running replicas" in _text(result)
    api.shell_connection.assert_not_called()
    bridge.assert_not_called()


@pytest.mark.parametrize("kind", sorted(COMMANDS))
def test_shell_requires_an_interactive_terminal(kind):
    target, args = COMMANDS[kind]
    client = _client()
    with patch(target, return_value=client):
        # CliRunner feeds pipes, not TTYs.
        result = CliRunner().invoke(lep, args)
    assert result.exit_code == 2, result.output
    assert "requires a terminal" in result.output
    for api in _apis(client).values():
        api.get_shell_replica.assert_not_called()


@pytest.mark.parametrize(
    "body, message",
    [
        (
            b'{"code":"PreconditionFailed","message":"devpod my-pod is stopped"}',
            "refused the shell connection (HTTP 412): devpod my-pod is stopped",
        ),
        (b"<html>gateway</html>", "refused the shell connection (HTTP 412)."),
    ],
)
def test_refused_handshake_reports_status_and_api_message(body, message):
    client = _client()
    client.pod.shell_connection.side_effect = websocket.WebSocketBadStatusException(
        "Handshake status 412 -+-+- {'set-cookie': 'secret'} -+-+- body",
        412,
        resp_headers={"set-cookie": "secret"},
        resp_body=body,
    )
    result, _, bridge = _invoke("pod", client=client)
    assert result.exit_code == 1
    assert message in _text(result)
    assert "secret" not in result.output
    bridge.assert_not_called()
