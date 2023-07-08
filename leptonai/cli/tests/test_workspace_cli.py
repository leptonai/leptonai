import os
import tempfile
import unittest

from click.testing import CliRunner
from loguru import logger

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import config
from leptonai.cli import lep as cli

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestWorkspaceCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["workspace", "login", "-r", "http://example-0.lepton.ai", "--dry-run"],
            input="test-workspace-0\n\n",
        )
        assert "logged in" in result.output.lower()
        assert result.exit_code == 0

    def test_workspace_login(self):
        runner = CliRunner()
        # If nothing, cannot log in
        result = runner.invoke(cli, ["workspace", "login"])
        self.assertIn("must specify", result.output.lower())
        self.assertEqual(result.exit_code, 1)
        # using -n name, OK
        result = runner.invoke(
            cli, ["workspace", "login", "-n", "test-workspace-0", "--dry-run"]
        )
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -n nonexisting name, not ok
        result = runner.invoke(
            cli,
            ["workspace", "login", "-n", "new-workspace", "--dry-run"],
            input="\n",  # empty auth token
        )
        self.assertIn(
            "https://new-workspace.cloud.lepton.ai/api/v1", result.output.lower()
        )
        self.assertIn("registered", result.output.lower())
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r, already registered, ok
        result = runner.invoke(
            cli, ["workspace", "login", "-r", "http://example-0.lepton.ai", "--dry-run"]
        )
        self.assertIn("already registered", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r -n together, both match, ok
        result = runner.invoke(
            cli,
            [
                "workspace",
                "login",
                "-r",
                "http://example-0.lepton.ai",
                "-n",
                "test-workspace-0",
                "--dry-run",
            ],
        )
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r -n together, not match, will go to registration
        result = runner.invoke(
            cli,
            [
                "workspace",
                "login",
                "-r",
                "http://example-0.lepton.ai",
                "-n",
                "non-matching-name",
                "--dry-run",
            ],
            input="\n",  # empty auth token
        )
        self.assertIn("registered", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r -n but not registered url, ok
        result = runner.invoke(
            cli,
            [
                "workspace",
                "login",
                "-r",
                "http://example-1.lepton.ai",
                "-n",
                "test-workspace-1",
                "--dry-run",
            ],
            input="\n",  # empty auth token
        )
        self.assertIn("registered", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r -n, not registered url, existing name, not ok
        result = runner.invoke(
            cli,
            [
                "workspace",
                "login",
                "-r",
                "http://example-1.lepton.ai",
                "-n",
                "test-workspace-0",
                "--dry-run",
            ],
            input="\n",  # empty auth token
        )
        self.assertIn("already registered", result.output.lower())
        self.assertNotEqual(result.exit_code, 0)

    def test_workspace_login_not_dryrun(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["workspace", "login", "-n", "test-workspace-0"])
        self.assertNotIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 1)

    def test_workspace_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["workspace", "list"])
        self.assertIn("test-workspace", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_workspace_logout(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["workspace", "logout"])
        self.assertIn("logged out", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_workspace_login_switch(self):
        runner = CliRunner()

        result = runner.invoke(
            cli,
            ["workspace", "login", "-r", "http://example-1.lepton.ai", "--dry-run"],
            input="test-workspace-1\n\n",
        )
        self.assertIn("test-workspace-1", result.output.lower())

        result = runner.invoke(
            cli,
            ["workspace", "login", "-n", "test-workspace-0", "--dry-run"],
        )
        self.assertIn("test-workspace-0", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_workspace_remove(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["workspace", "login", "-n", "test-workspace-0", "--dry-run"]
        )
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        result = runner.invoke(cli, ["workspace", "remove", "-n", "test-workspace-0"])
        self.assertIn("removed", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        result = runner.invoke(
            cli, ["workspace", "remove", "-n", "nonexistent-workspace"]
        )
        self.assertIn("does not exist", result.output.lower())
        self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
