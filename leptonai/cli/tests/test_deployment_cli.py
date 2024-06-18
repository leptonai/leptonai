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


class TestDeploymentCliLocal(unittest.TestCase):
    def test_deployment_local(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["deployment", "list"])
        self.assertNotEqual(result.exit_code, 0)
        # self.assertIn("It seems that you are not logged in", result.output)


if __name__ == "__main__":
    unittest.main()
