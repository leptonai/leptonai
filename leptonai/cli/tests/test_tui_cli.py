import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner

from leptonai.cli import lep
from leptonai.cli.tui import _cli_auth_env


def _completed(returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode)


def _no_auth_env():
    return patch("leptonai.cli.tui._cli_auth_env", return_value=None)


def test_tui_command_is_registered():
    result = CliRunner().invoke(lep, ["tui", "--help"])

    assert result.exit_code == 0, result.output
    assert "lep-tui" in result.output


def test_tui_installs_when_missing_then_launches_with_passthrough_args():
    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value=None),
        patch("leptonai.cli.tui._install_tui", return_value="/fake/lep-tui") as install,
        patch("leptonai.cli.tui.subprocess.run", return_value=_completed()) as run,
        _no_auth_env(),
    ):
        result = CliRunner().invoke(lep, ["tui", "--mock", "jobs"])

    assert result.exit_code == 0, result.output
    install.assert_called_once_with(None)
    run.assert_called_once_with(
        ["/fake/lep-tui", "--mock", "jobs"], check=False, env=None
    )


def test_tui_updates_before_launch_and_propagates_exit_code():
    calls = []

    def record(argv, check, **kwargs):
        calls.append(argv)
        return _completed(3 if len(calls) > 1 else 0)

    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value="/fake/lep-tui"),
        patch("leptonai.cli.tui.subprocess.run", side_effect=record),
        _no_auth_env(),
    ):
        result = CliRunner().invoke(lep, ["tui"])

    assert calls == [["/fake/lep-tui", "update"], ["/fake/lep-tui"]]
    assert result.exit_code == 3, result.output


def test_tui_no_update_skips_the_self_update():
    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value="/fake/lep-tui"),
        patch("leptonai.cli.tui.subprocess.run", return_value=_completed()) as run,
        _no_auth_env(),
    ):
        result = CliRunner().invoke(lep, ["tui", "--no-update"])

    assert result.exit_code == 0, result.output
    run.assert_called_once_with(["/fake/lep-tui"], check=False, env=None)


def test_tui_version_pin_flows_into_update_target():
    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value="/fake/lep-tui"),
        patch("leptonai.cli.tui.subprocess.run", return_value=_completed()) as run,
        _no_auth_env(),
    ):
        result = CliRunner().invoke(lep, ["tui", "--tui-version", "0.1.0"])

    assert result.exit_code == 0, result.output
    assert run.call_args_list[0].args[0] == [
        "/fake/lep-tui",
        "update",
        "--target",
        "0.1.0",
    ]


def test_tui_version_pin_conflicts_with_no_update():
    result = CliRunner().invoke(lep, ["tui", "--no-update", "--tui-version", "0.1.0"])

    assert result.exit_code == 2, result.output
    assert "--no-update" in result.output


def test_tui_failed_update_still_launches():
    calls = []

    def record(argv, check, **kwargs):
        calls.append(argv)
        return _completed(1 if argv[-1] == "update" else 0)

    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value="/fake/lep-tui"),
        patch("leptonai.cli.tui.subprocess.run", side_effect=record),
        _no_auth_env(),
    ):
        result = CliRunner().invoke(lep, ["tui"])

    assert result.exit_code == 0, result.output
    assert calls == [["/fake/lep-tui", "update"], ["/fake/lep-tui"]]
    assert "self-update failed" in result.output


def test_tui_installer_download_failure_mentions_the_network():
    import requests

    failing = Mock()
    failing.RequestException = requests.RequestException
    failing.get.side_effect = requests.RequestException("boom")
    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value=None),
        patch.dict("sys.modules", {"requests": failing}),
    ):
        result = CliRunner().invoke(lep, ["tui"])

    assert result.exit_code == 1, result.output
    assert "VPN" in result.output


def test_tui_installer_uses_pinned_version_url_and_flag():
    response = Mock()
    response.text = "#!/bin/sh\nexit 0\n"
    response.raise_for_status.return_value = None
    fake_requests = Mock()
    fake_requests.get.return_value = response
    import requests

    fake_requests.RequestException = requests.RequestException
    with (
        patch("leptonai.cli.tui._find_tui_binary", side_effect=[None, "/fake/lep-tui"]),
        patch.dict("sys.modules", {"requests": fake_requests}),
        patch("leptonai.cli.tui.subprocess.run", return_value=_completed()) as run,
        _no_auth_env(),
    ):
        result = CliRunner().invoke(lep, ["tui", "--tui-version", "0.2.0-rc.1"])

    assert result.exit_code == 0, result.output
    fake_requests.get.assert_called_once_with(
        "https://gitlab-master.nvidia.com/api/v4/projects/186903"
        "/packages/generic/lep-tui/0.2.0-rc.1/install.sh",
        timeout=15,
    )
    installer_argv = run.call_args_list[0].args[0]
    assert installer_argv[0] == "sh"
    assert installer_argv[2:] == ["--version", "0.2.0-rc.1"]
    assert run.call_args_list[1].args[0] == ["/fake/lep-tui"]


def _fake_record(workspace_id, token, url="https://gw.example.com/api/v2/x"):
    record = Mock()
    record.get_current_workspace_id.return_value = workspace_id
    record.current.return_value = (
        None
        if workspace_id is None
        else SimpleNamespace(auth_token=token, url=url, id_=workspace_id)
    )
    return record


def test_cli_auth_env_projects_the_current_workspace():
    record = _fake_record("ws1", "nvapi-secret")
    with (
        patch("leptonai.api.v2.workspace_record.WorkspaceRecord", record),
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("LEPTON_WORKSPACE", None)
        os.environ.pop("LEPTON_AUTH_TOKEN", None)
        env = _cli_auth_env()

    assert env == {
        "LEPTON_WORKSPACE": "ws1",
        "LEPTON_AUTH_TOKEN": "nvapi-secret",
        "LEPTON_API_URL": "https://gw.example.com/api/v2/x",
    }


def test_cli_auth_env_refuses_unusable_states():
    # A token shape lep-tui rejects must not be handed over.
    with patch(
        "leptonai.api.v2.workspace_record.WorkspaceRecord",
        _fake_record("ws1", "legacy-token"),
    ):
        assert _cli_auth_env() is None
    # No current workspace.
    with patch(
        "leptonai.api.v2.workspace_record.WorkspaceRecord",
        _fake_record(None, None),
    ):
        assert _cli_auth_env() is None
    # Caller-provided TUI variables win over projection.
    with (
        patch(
            "leptonai.api.v2.workspace_record.WorkspaceRecord",
            _fake_record("ws1", "nvapi-secret"),
        ),
        patch.dict(os.environ, {"LEPTON_AUTH_TOKEN": "nvapi-mine"}),
    ):
        assert _cli_auth_env() is None


def test_tui_launches_with_projected_credentials():
    overrides = {
        "LEPTON_WORKSPACE": "ws1",
        "LEPTON_AUTH_TOKEN": "nvapi-secret",
        "LEPTON_API_URL": "https://gw.example.com/api/v2/x",
    }
    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value="/fake/lep-tui"),
        patch("leptonai.cli.tui._cli_auth_env", return_value=dict(overrides)),
        patch("leptonai.cli.tui.subprocess.run", return_value=_completed()) as run,
    ):
        result = CliRunner().invoke(lep, ["tui", "--no-update"])

    assert result.exit_code == 0, result.output
    assert "ws1" in result.output
    launch_env = run.call_args.kwargs["env"]
    for key, value in overrides.items():
        assert launch_env[key] == value
    assert "PATH" in launch_env  # merged over os.environ, not replacing it


def test_tui_no_auth_skips_credential_projection():
    with (
        patch("leptonai.cli.tui._find_tui_binary", return_value="/fake/lep-tui"),
        patch("leptonai.cli.tui._cli_auth_env") as project,
        patch("leptonai.cli.tui.subprocess.run", return_value=_completed()) as run,
    ):
        result = CliRunner().invoke(lep, ["tui", "--no-update", "--no-auth"])

    assert result.exit_code == 0, result.output
    project.assert_not_called()
    run.assert_called_once_with(["/fake/lep-tui"], check=False, env=None)
