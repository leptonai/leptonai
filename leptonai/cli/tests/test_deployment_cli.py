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


logger.info(f"Using cache dir: {config.CACHE_DIR}")


class _FakeDeploymentAPI:
    def __init__(self):
        self.created_spec = None

    def list_all(self):
        return []

    def create(self, spec):
        self.created_spec = spec
        return True


class _FakeAPIClient:
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.deployment = _FakeDeploymentAPI()
        _FakeAPIClient.last_instance = self


class TestDeploymentCliLocal(unittest.TestCase):
    def test_deployment_local(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["deployment", "list"])
        self.assertNotEqual(result.exit_code, 0)
        # self.assertIn("It seems that you are not logged in", result.output)

    def test_deployment_create_parses_protocol_from_container_port(self):
        runner = CliRunner()

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "deployment",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--container-port",
                    "8080:tcp",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertIsNotNone(created)
        self.assertEqual(created.spec.container.ports[0].container_port, 8080)
        self.assertEqual(created.spec.container.ports[0].protocol, "TCP")

    def test_deployment_create_port_only_leaves_protocol_unset(self):
        runner = CliRunner()

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "deployment",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--container-port",
                    "8080",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertIsNotNone(created)
        self.assertEqual(created.spec.container.ports[0].container_port, 8080)
        self.assertIsNone(created.spec.container.ports[0].protocol)


if __name__ == "__main__":
    unittest.main()
