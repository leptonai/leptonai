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
        self.assertIn("logged out", result.output.lower())
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
