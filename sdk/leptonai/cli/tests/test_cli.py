import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from click.testing import CliRunner
from loguru import logger

from leptonai import config, __version__
from leptonai.cli import lep as cli


logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestLepCli(unittest.TestCase):
    def test_version(self):
        runner = CliRunner()

        v = runner.invoke(cli, ["-v"])
        version = runner.invoke(cli, ["--version"])

        self.assertEqual(v.exit_code, 0)
        self.assertEqual(version.exit_code, 0)
        self.assertEqual(v.output.strip(), f"lep, version {__version__}")
        self.assertEqual(version.output.strip(), f"lep, version {__version__}")


if __name__ == "__main__":
    unittest.main()
