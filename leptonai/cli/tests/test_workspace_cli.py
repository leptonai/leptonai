import os
import tempfile
import unittest
from unittest import mock

from click.testing import CliRunner
from loguru import logger

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import config
from leptonai.api.v2.utils import WorkspaceForbiddenError
from leptonai.api.v2.workspace_record import WorkspaceRecord
from leptonai.cli import lep as cli

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestWorkspaceCli(unittest.TestCase):
    def test_workspace_login_not_dryrun(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["workspace", "login", "-i", "nonexistent-workspace-for-test"]
        )
        self.assertNotIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 1)

    def test_workspace_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["workspace", "list"])
        self.assertEqual(result.exit_code, 0)

    def test_workspace_logout(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["workspace", "logout"])
        self.assertIn("not logged in to any workspace.", result.output.lower())
        self.assertEqual(result.exit_code, 0)


class TestWorkspaceLogin(unittest.TestCase):
    def _invoke_login(self, fake_client):
        runner = CliRunner()
        with (
            mock.patch.object(WorkspaceRecord, "has", return_value=False),
            mock.patch.object(WorkspaceRecord, "set_or_exit") as set_or_exit,
            mock.patch(
                "leptonai.cli.workspace.APIClient", return_value=fake_client
            ) as api_client_cls,
        ):
            result = runner.invoke(
                cli, ["workspace", "login", "-i", "stag", "-t", "nvapi-faketoken"]
            )
        return result, set_or_exit, api_client_cls

    def test_login_forbidden_prints_url_check_hint_and_does_not_persist(self):
        fake_client = mock.Mock()
        fake_client.info.side_effect = WorkspaceForbiddenError(
            workspace_id="stag",
            workspace_url=config.API_URL_BASE + "/api/v2/workspaces/stag",
            auth_token="nv****98",
        )
        result, set_or_exit, _ = self._invoke_login(fake_client)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Workspace Access Forbidden", result.output)
        self.assertIn("--workspace-url", result.output)
        set_or_exit.assert_not_called()

    def test_login_verifies_default_url_before_persisting(self):
        fake_client = mock.Mock()
        fake_client.info.return_value = mock.Mock(
            workspace_name="lepton-stag", workspace_tier="basic", build_time="today"
        )
        fake_client.version.return_value = (0, 1, 0)
        result, set_or_exit, api_client_cls = self._invoke_login(fake_client)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Logged in to your workspace", result.output)
        api_client_cls.assert_called_once_with(
            "stag",
            "nvapi-faketoken",
            config.API_URL_BASE + "/api/v2/workspaces/stag",
            None,
        )
        set_or_exit.assert_called_once_with(
            "stag",
            auth_token="nvapi-faketoken",
            url=config.API_URL_BASE + "/api/v2/workspaces/stag",
            workspace_origin_url=None,
            could_be_new_token=True,
        )


class TestLepLogin(unittest.TestCase):
    def test_login_with_credentials_forbidden_does_not_persist(self):
        runner = CliRunner()
        fake_client = mock.Mock()
        fake_client.info.side_effect = WorkspaceForbiddenError(
            workspace_id="stag",
            workspace_url=config.API_URL_BASE + "/api/v2/workspaces/stag",
            auth_token="nv****98",
        )
        with (
            mock.patch.object(WorkspaceRecord, "set_or_exit") as set_or_exit,
            mock.patch("leptonai.cli.cli.APIClient", return_value=fake_client),
        ):
            result = runner.invoke(cli, ["login", "-c", "stag:nvapi-faketoken"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Workspace Access Forbidden", result.output)
        set_or_exit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
