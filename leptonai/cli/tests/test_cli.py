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
from leptonai.cli.photon import _sequentialize_pip_commands


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


class TestPipSequences(unittest.TestCase):
    def test_sequence_correctness(self):
        sequences = [
            ["numpy"],
            ["numpy", "scipy"],
            ["numpy", "scipy", "uninstall numpy", "torch", "numpy"],
            ["numpy", "scipy", "uninstall numpy", "uninstall scipy", "torch", "numpy"],
            [
                "numpy",
                "git+http://github.com/leptonai/leptonai/",
                "uninstall numpy",
                "scipy",
                "torch",
                "numpy",
                "uninstall scipy",
            ],
        ]
        expected_outputs = [
            [("install", ["numpy"])],
            [("install", ["numpy", "scipy"])],
            [
                ("install", ["numpy", "scipy"]),
                ("uninstall", ["numpy"]),
                ("install", ["torch", "numpy"]),
            ],
            [
                ("install", ["numpy", "scipy"]),
                ("uninstall", ["numpy", "scipy"]),
                ("install", ["torch", "numpy"]),
            ],
            [
                ("install", ["numpy", "git+http://github.com/leptonai/leptonai/"]),
                ("uninstall", ["numpy"]),
                ("install", ["scipy", "torch", "numpy"]),
                ("uninstall", ["scipy"]),
            ],
        ]
        for sequence, expected in zip(sequences, expected_outputs):
            self.assertEqual(
                _sequentialize_pip_commands(sequence),
                expected,
                f"Sequence {sequence} was not parsed correctly",
            )

    def test_sequence_correctness_edge_cases(self):
        edge_cases = [
            [],  # Empty list
            ["numpy", "scipy", "torch"],  # Only installations
            ["numpy", "numpy", "scipy", "torch"],  # Duplicated installations
            [
                "uninstall numpy",
                "uninstall scipy",
                "uninstall torch",
            ],  # Only uninstallations
            [
                "uninstall numpy",
                "uninstall numpy",
                "uninstall scipy",
                "uninstall torch",
            ],  # Duplicated uninstallations
            ["numpy", "uninstall scipy", "torch", "uninstall numpy"],  # Interleaved
            [
                "numpy_uninstall"
            ],  # Includes the word uninstall but isn't an uninstall command
            [
                "uninstall uninstall numpy"
            ],  # odd case, whch we don't handle and will interpret this as pip uninstall-ing two packages, named uninstall and numpy.
        ]
        expected_outputs = [
            [],
            [("install", ["numpy", "scipy", "torch"])],
            [("install", ["numpy", "scipy", "torch"])],
            [("uninstall", ["numpy", "scipy", "torch"])],
            [("uninstall", ["numpy", "scipy", "torch"])],
            [
                ("install", ["numpy"]),
                ("uninstall", ["scipy"]),
                ("install", ["torch"]),
                ("uninstall", ["numpy"]),
            ],
            [("install", ["numpy_uninstall"])],
            [("uninstall", ["uninstall numpy"])],
        ]
        for sequence, expected in zip(edge_cases, expected_outputs):
            self.assertEqual(
                _sequentialize_pip_commands(sequence),
                expected,
                f"Sequence {sequence} was not parsed correctly",
            )


if __name__ == "__main__":
    unittest.main()
