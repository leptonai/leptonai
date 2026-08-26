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
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.job import LeptonJob
from leptonai.cli import lep as cli


logger.info(f"Using cache dir: {config.CACHE_DIR}")


class _FakeJobAPI:
    def __init__(self):
        self.created_job = None

    def create(self, job):
        self.created_job = job
        return LeptonJob(metadata=Metadata(id="job-123"), spec=job.spec)


class _FakeAPIClient:
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.job = _FakeJobAPI()
        _FakeAPIClient.last_instance = self


def _create_args(*extra):
    return [
        "job",
        "create",
        "--name",
        "test-job",
        "--container-image",
        "nginx:latest",
        "--command",
        "echo done",
        "--resource-shape",
        config.DEFAULT_RESOURCE_SHAPE,
        *extra,
    ]


class TestJobCliStorageAttachment(unittest.TestCase):
    def test_job_create_builds_storage_attachments(self):
        runner = CliRunner()
        _FakeAPIClient.last_instance = None

        with patch("leptonai.cli.job.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                _create_args(
                    "--storage-attachment",
                    "my-bucket:awsProfile",
                    "--storage-attachment",
                    "my-bucket:mscProfile:object.aistore:my-profile",
                ),
            )

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertIsNotNone(created)
        attachments = created.spec.storage_attachments
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].data_source_name, "my-bucket")
        self.assertEqual(len(attachments[0].attachments), 2)
        self.assertEqual(attachments[0].attachments[0].mode, "awsProfile")
        self.assertIsNone(attachments[0].attachments[0].attach_with)
        self.assertEqual(attachments[0].attachments[1].mode, "mscProfile")
        self.assertEqual(attachments[0].attachments[1].attach_with, "object.aistore")
        self.assertEqual(attachments[0].attachments[1].profile_name, "my-profile")

    def test_job_create_without_storage_attachment_leaves_field_unset(self):
        runner = CliRunner()
        _FakeAPIClient.last_instance = None

        with patch("leptonai.cli.job.APIClient", _FakeAPIClient):
            result = runner.invoke(cli, _create_args())

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertIsNotNone(created)
        self.assertIsNone(created.spec.storage_attachments)

    def test_job_create_rejects_invalid_storage_attachment_mode(self):
        runner = CliRunner()
        _FakeAPIClient.last_instance = None

        with patch("leptonai.cli.job.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                _create_args("--storage-attachment", "my-bucket:not-a-mode"),
            )

        self.assertEqual(result.exit_code, 1, result.output)
        output = " ".join(((result.output or "") + (result.stderr or "")).split())
        self.assertIn("Error parsing --storage-attachment", output)
        self.assertIn("MODE must be one of", output)
        self.assertIsNotNone(_FakeAPIClient.last_instance)
        self.assertIsNone(_FakeAPIClient.last_instance.job.created_job)


if __name__ == "__main__":
    unittest.main()
