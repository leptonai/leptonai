"""Exercise client preflight through both SSH commands without a real tsh."""

from datetime import datetime, timedelta, timezone
import json
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from leptonai.api.v2.types.teleport import TeleportConnection
from leptonai.cli.job import job
from leptonai.cli.pod import pod


@pytest.fixture(params=["pod", "job", "job-explicit-proxy"])
def session(request):
    connection = TeleportConnection(
        name="ws-worker",
        status="Running",
        proxy="proxy.example.com",
        port=443,
        clusterDomain="proxy.example.com",
        username="root",
    )
    client = SimpleNamespace(
        workspace_id="ws",
        pod=SimpleNamespace(get_teleport_connection=Mock(return_value=connection)),
        job=SimpleNamespace(get_ssh_replica=Mock(return_value="worker")),
    )
    if request.param == "pod":
        module, command, args = (
            "pod",
            pod,
            ["ssh", "-n", "pod", "--transport", "teleport"],
        )
    else:
        module, command, args = "job", job, ["ssh", "--id", "job"]
        if request.param == "job-explicit-proxy":
            args += ["--teleport-proxy", "proxy.example.com"]
    with (
        patch(f"leptonai.cli.{module}.APIClient", return_value=client),
        patch(
            "leptonai.cli.teleport.shutil.which", return_value="/usr/bin/tsh"
        ) as which,
        patch("leptonai.cli.teleport.subprocess.run") as run,
    ):
        yield lambda: CliRunner().invoke(command, args), which, run


def completed(stdout="", code=0):
    return subprocess.CompletedProcess([], code, stdout, "")


@pytest.mark.parametrize(
    "version",
    [
        "Teleport v18.0.0 git:abc go1.24.0\n",
        "Teleport Enterprise v18.2.5 git:abc\n",
        "Teleport v19.0.0-dev+build.1 git:abc\n",
        (
            "Teleport v18.6.2 git:abc\nProxy version: 17.0.0\n"
            "Re-executed from version: 17.0.0\n"
        ),
    ],
)
def test_supported_client_is_checked_once_before_profiles_and_ssh(session, version):
    invoke, _, run = session

    def execute(args, **kwargs):
        if args[1] == "version":
            return completed(version)
        if args[1] == "status":
            return completed(
                json.dumps({
                    "active": {
                        "profile_url": "https://proxy.example.com",
                        "cluster": "proxy.example.com",
                        "username": "alice@example.com",
                        "logins": ["root"],
                        "valid_until": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                    }
                })
            )
        if args[1] == "ls":
            return completed(
                json.dumps([{
                    "kind": "node",
                    "metadata": {
                        "name": "node-id",
                        "labels": {"teleport.lepton.ai/workspace": "ws"},
                    },
                    "spec": {"hostname": "ws-worker"},
                }])
            )
        assert args[1] == "ssh"
        return completed()

    run.side_effect = execute
    result = invoke()
    assert result.exit_code == 0, result.output
    commands = [call.args[0][1] for call in run.call_args_list]
    assert commands[0] == "version"
    assert commands.count("version") == 1
    assert commands[-1] == "ssh"
    assert run.call_args_list[0].kwargs == {
        "stdin": subprocess.DEVNULL,
        "capture_output": True,
        "text": True,
        "timeout": 10,
    }


@pytest.mark.parametrize(
    "version",
    [
        "Teleport v17.9.9 git:abc\n",
        "Teleport v9.0.0\n",
        "Teleport v17.9.9\nProxy version: 18.11.0\nRe-executed from version: 18.7.3\n",
    ],
)
def test_old_client_blocks_profile_login_and_ssh(session, version):
    invoke, _, run = session
    run.return_value = completed(version)
    result = invoke()
    assert result.exit_code == 1
    assert "requires tsh v18 or newer" in result.output
    assert "Upgrade" in result.output
    assert "goteleport.com" in result.output
    assert run.call_count == 1
    assert run.call_args.args[0] == ["/usr/bin/tsh", "version"]


@pytest.mark.parametrize(
    "version",
    ["", "garbage", "Proxy version: 18.11.0", "Teleport v18", "Teleport v18.0.0oops"],
)
def test_unknown_version_fails_before_profiles_or_login(session, version):
    invoke, _, run = session
    run.return_value = completed(version)
    result = invoke()
    assert result.exit_code == 1
    assert "Could not determine" in result.output
    assert "requires tsh v18 or newer" in result.output
    assert run.call_count == 1


@pytest.mark.parametrize(
    "failure, message, code",
    [
        (completed("Teleport v18.0.0", code=2), "exited with status 2", 1),
        (subprocess.TimeoutExpired("tsh version", 10), "Timed out", 1),
        (FileNotFoundError("tsh disappeared"), "Could not run Teleport", 1),
        (KeyboardInterrupt(), "", 130),
    ],
)
def test_failed_version_check_does_not_continue(session, failure, message, code):
    invoke, _, run = session
    run.side_effect = [failure]
    result = invoke()
    assert result.exit_code == code, result.output
    assert message in result.output
    assert run.call_count == 1


def test_missing_client_has_installation_and_minimum_version_hint(session):
    invoke, which, run = session
    which.return_value = None
    result = invoke()
    assert result.exit_code == 1
    assert "not found in PATH" in result.output
    assert "tsh v18 or newer" in result.output
    assert "goteleport.com" in result.output
    run.assert_not_called()
