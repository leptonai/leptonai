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


class TestRemoteCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["remote", "login", "-r", "http://example-0.lepton.ai", "--dry-run"],
            input="test-remote-0\n\n",
        )
        assert "logged in" in result.output.lower()
        assert result.exit_code == 0

    def test_remote_login(self):
        runner = CliRunner()
        # If nothing, cannot log in
        result = runner.invoke(cli, ["remote", "login"])
        self.assertIn("must specify", result.output.lower())
        self.assertEqual(result.exit_code, 1)
        # using -n name, OK
        result = runner.invoke(
            cli, ["remote", "login", "-n", "test-remote-0", "--dry-run"]
        )
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -n nonexisting name, not ok
        result = runner.invoke(
            cli, ["remote", "login", "-n", "nonexistent-remote", "--dry-run"]
        )
        self.assertIn("does not exist", result.output.lower())
        self.assertEqual(result.exit_code, 1)
        # using -r, already registered, ok
        result = runner.invoke(
            cli, ["remote", "login", "-r", "http://example-0.lepton.ai", "--dry-run"]
        )
        self.assertIn("already registered", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r -n together, both match, ok
        result = runner.invoke(
            cli,
            [
                "remote",
                "login",
                "-r",
                "http://example-0.lepton.ai",
                "-n",
                "test-remote-0",
                "--dry-run",
            ],
        )
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        # using -r -n together, not match, will go to registration
        result = runner.invoke(
            cli,
            [
                "remote",
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
                "remote",
                "login",
                "-r",
                "http://example-1.lepton.ai",
                "-n",
                "test-remote-1",
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
                "remote",
                "login",
                "-r",
                "http://example-1.lepton.ai",
                "-n",
                "test-remote-0",
                "--dry-run",
            ],
            input="\n",  # empty auth token
        )
        self.assertIn("already registered", result.output.lower())
        self.assertNotEqual(result.exit_code, 0)

    def test_remote_login_not_dryrun(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remote", "login", "-n", "test-remote-0"])
        self.assertNotIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 1)

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
            ["remote", "login", "-r", "http://example-1.lepton.ai", "--dry-run"],
            input="test-remote-1\n\n",
        )
        self.assertIn("test-remote-1", result.output.lower())

        result = runner.invoke(
            cli,
            ["remote", "login", "-n", "test-remote-0", "--dry-run"],
        )
        self.assertIn("test-remote-0", result.output.lower())
        self.assertEqual(result.exit_code, 0)

    def test_remote_remove(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["remote", "login", "-n", "test-remote-0", "--dry-run"]
        )
        self.assertIn("logged in", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        result = runner.invoke(cli, ["remote", "remove", "-n", "test-remote-0"])
        self.assertIn("removed", result.output.lower())
        self.assertEqual(result.exit_code, 0)
        result = runner.invoke(cli, ["remote", "remove", "-n", "nonexistent-remote"])
        self.assertIn("does not exist", result.output.lower())
        self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
