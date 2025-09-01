import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
from unittest.mock import patch

from click.testing import CliRunner
from loguru import logger

from leptonai import config
from leptonai.cli import lep as cli
from leptonai.api.v1.types.common import Metadata
from leptonai.api.v1.types.deployment import (
    LeptonDeployment,
    LeptonDeploymentUserSpec,
)


logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestDeploymentCliLocal(unittest.TestCase):
    def test_deployment_local(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["deployment", "list"])
        self.assertNotEqual(result.exit_code, 0)
        # self.assertIn("It seems that you are not logged in", result.output)

    def test_update_without_autoscale_flags_excludes_autoscaler_payload(self):
        runner = CliRunner()

        class FakeDeploymentAPI:
            def __init__(self):
                self.last_spec = None

            def get(self, name):
                # Return minimal valid deployment object for update flow
                return LeptonDeployment(
                    metadata=Metadata(id=name, name=name),
                    spec=LeptonDeploymentUserSpec(),
                )

            def update(self, name_or_deployment, spec, dryrun=False):
                # Capture the full LeptonDeployment sent by CLI
                self.last_spec = spec
                # Echo back a LeptonDeployment-like object
                return spec

        class FakeAPIClient:
            def __init__(self, *args, **kwargs):
                self.deployment = FakeDeploymentAPI()

        with patch("leptonai.cli.deployment.APIClient", new=lambda *a, **k: FakeAPIClient()):
            # Act: run update without any autoscaling-related flags
            result = runner.invoke(
                cli,
                [
                    "endpoint",
                    "update",
                    "-n",
                    "unit-test-ep",
                    "--shared-memory-size",
                    "128",
                ],
            )

            # Assert CLI completed (Fake client prevents network/login)
            self.assertEqual(result.exit_code, 0, msg=result.output)

        # Re-run with grab-able instance
        captured = {"last": None}

        class GrabbableAPIClient:
            def __init__(self, *args, **kwargs):
                self.deployment = FakeDeploymentAPI()
                captured["last"] = self.deployment

        with patch("leptonai.cli.deployment.APIClient", new=lambda *a, **k: GrabbableAPIClient()):
            result = runner.invoke(
                cli,
                [
                    "endpoint",
                    "update",
                    "-n",
                    "unit-test-ep",
                    "--shared-memory-size",
                    "128",
                ],
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)

            sent_spec = captured["last"].last_spec  # type: ignore
            self.assertIsNotNone(sent_spec)
            # sent_spec is a LeptonDeployment instance
            self.assertIsNotNone(sent_spec.spec)

            # Core assertion: without autoscale-related flags, autoscaler should not be sent
            self.assertIsNone(
                sent_spec.spec.auto_scaler,
                msg=f"Did not expect auto_scaler to be set, payload: {sent_spec.model_dump()}",
            )


if __name__ == "__main__":
    unittest.main()
