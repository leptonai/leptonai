import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from click.testing import CliRunner
from loguru import logger

from leptonai import config
from leptonai.cli import lep as cli

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestIngressCliLocal(unittest.TestCase):
    def test_ingress_import(self):
        """Test that ingress commands can be imported without errors."""
        runner = CliRunner()

        # Test ingress help command works
        result = runner.invoke(cli, ["ingress", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ingress", result.output.lower())

    def test_ingress_list_no_auth(self):
        """Test that ingress list fails gracefully when not authenticated."""
        runner = CliRunner()

        # Should fail because not authenticated, but should not crash
        result = runner.invoke(cli, ["ingress", "list"])
        # Exit code will be non-zero due to auth failure
        self.assertNotEqual(result.exit_code, 0)

    def test_add_endpoint_help(self):
        """Test that add-endpoint command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "add-endpoint", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("add-endpoint", result.output.lower())
        self.assertIn("canary", result.output.lower())

    def test_update_endpoint_help(self):
        """Test that update-endpoint command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "update-endpoint", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("update-endpoint", result.output.lower())

    def test_set_endpoints_help(self):
        """Test that set-endpoints command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "set-endpoints", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("set-endpoints", result.output.lower())

    def test_remove_endpoint_help(self):
        """Test that remove-endpoint command help works."""
        runner = CliRunner()

        result = runner.invoke(cli, ["ingress", "remove-endpoint", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("remove-endpoint", result.output.lower())


if __name__ == "__main__":
    unittest.main()
