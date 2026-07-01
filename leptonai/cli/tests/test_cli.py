import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from click.testing import CliRunner
from loguru import logger

from leptonai import config, __version__
from leptonai.api.v2.spec_utils import make_mounts_from_strings
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

    def test_reject_empty_string_option(self):
        runner = CliRunner()
        # Use a representative command that requires a string
        # For example: `lep secret create --name ""` should fail
        result = runner.invoke(cli, ["secret", "create", "--name", ""])  # type: ignore
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("empty", (result.output or "") + (result.stderr or ""))

    def test_make_mounts_rejects_named_volume_without_storage_name(self):
        with self.assertRaisesRegex(ValueError, "missing storage_name"):
            make_mounts_from_strings(["/hf-cache:/root/.cache/huggingface:node-nfs"])

    def test_make_mounts_accepts_named_volume_with_storage_name(self):
        mounts = make_mounts_from_strings(
            ["/hf-cache:/root/.cache/huggingface:node-nfs:my-nfs"]
        )

        self.assertIsNotNone(mounts)
        self.assertEqual(mounts[0].path, "/hf-cache")  # type: ignore[index]
        self.assertEqual(mounts[0].mount_path, "/root/.cache/huggingface")  # type: ignore[index]
        self.assertEqual(mounts[0].from_, "node-nfs:my-nfs")  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
