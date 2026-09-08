import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

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


class TestJobListFilters(unittest.TestCase):
    def _invoke(self, args, jobs=None):
        client = SimpleNamespace(
            job=SimpleNamespace(list_all=Mock(return_value=list(jobs or []))),
            get_dashboard_base_url=lambda: None,
        )
        with patch("leptonai.cli.job.get_client", return_value=client):
            result = CliRunner().invoke(cli, ["job", "list", *args])
        return result, client.job.list_all

    def test_job_list_passes_labels_as_a_label_selector(self):
        result, list_all = self._invoke(
            ["-l", "team:research", "--label", "env=prod", "-l", "owner"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        kwargs = list_all.call_args.kwargs
        self.assertEqual(kwargs["query"], "team=research,env=prod,owner")
        self.assertEqual(kwargs["job_query_mode"], "alive_only")
        self.assertIn("No jobs match the specified filters.", result.output)

    def test_job_list_without_filters_sends_no_selector(self):
        result, list_all = self._invoke([])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("query", list_all.call_args.kwargs)
        self.assertNotIn("No jobs match the specified filters.", result.output)

    def test_job_list_include_archived_uses_the_archive_query_mode(self):
        result, list_all = self._invoke(["-ia", "-u", "alice"])
        self.assertEqual(result.exit_code, 0, result.output)
        kwargs = list_all.call_args.kwargs
        self.assertEqual(kwargs["job_query_mode"], "alive_and_archive")
        self.assertEqual(kwargs["created_by"], ["alice"])
        self.assertIn("No jobs matched your filters.", result.output)

    def test_job_list_state_help_is_derived_from_the_enum(self):
        result = CliRunner().invoke(cli, ["job", "list", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Terminating", result.output)
        self.assertIn("-l, --label", result.output)
