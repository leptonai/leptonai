import os
import tempfile
import unittest

from click.testing import CliRunner
from loguru import logger

from leptonai import config
from leptonai.cli import lep as cli

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir
logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestRemoteCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remote", "login", "-r", "http://example-0.lepton.ai"],
            input="test-remote-0\n\n",
        )
        assert "logged in" in result.output.lower()
        assert result.exit_code == 0

    def test_remote_login(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remote", "login", "-n", "test-remote-0"])
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_remote_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remote", "list"])
        self.assertIn("test-remote", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_remote_logout(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remote", "logout"])
        self.assertIn("logged out", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_remote_login_switch(self):
        runner = CliRunner()

        result = runner.invoke(
            cli,
            ["remote", "login", "-r", "http://example-1.lepton.ai"],
            input="test-remote-1\n\n",
        )
        self.assertIn("test-remote-1", result.output.lower())

        result = runner.invoke(
            cli,
            ["remote", "login", "-n", "test-remote-0"],
        )
        self.assertIn("test-remote-0", result.output.lower())
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
