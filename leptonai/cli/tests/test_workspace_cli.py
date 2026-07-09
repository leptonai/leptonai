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


class TestWorkspaceLoginForbidden(unittest.TestCase):
    def test_login_forbidden_prints_url_check_hint(self):
        runner = CliRunner()
        fake_client = mock.Mock()
        fake_client.info.side_effect = WorkspaceForbiddenError(
            workspace_id="stag",
            workspace_url=config.API_URL_BASE + "/api/v2/workspaces/stag",
            auth_token="nv****98",
        )
        with (
            mock.patch.object(WorkspaceRecord, "has", return_value=False),
            mock.patch.object(WorkspaceRecord, "set_or_exit"),
            mock.patch.object(WorkspaceRecord, "client", return_value=fake_client),
        ):
            result = runner.invoke(
                cli, ["workspace", "login", "-i", "stag", "-t", "nvapi-faketoken"]
            )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Workspace Access Forbidden", result.output)
        self.assertIn("--workspace-url", result.output)


if __name__ == "__main__":
    unittest.main()
