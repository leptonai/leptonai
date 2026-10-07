import json
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


class TestJobCreateNodeLabelSelector(unittest.TestCase):
    def _invoke(self, extra, spec_file=None):
        _FakeAPIClient.last_instance = None
        args = _create_args(*extra)
        if spec_file is not None:
            args.extend(["--file", spec_file])
        with patch("leptonai.cli.job.APIClient", _FakeAPIClient):
            result = CliRunner().invoke(cli, args)
        return result

    def _write_spec(self, affinity):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(
            {
                "resource_shape": config.DEFAULT_RESOURCE_SHAPE,
                "container": {"image": "nginx:latest"},
                "affinity": affinity,
            },
            handle,
        )
        handle.close()
        self.addCleanup(os.remove, handle.name)
        return handle.name

    def test_job_create_sets_node_label_selector(self):
        result = self._invoke(
            ["--node-label-selector", "  vmss=1,fabric,!maintenance  "]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertEqual(
            created.spec.affinity.node_label_selector, "vmss=1,fabric,!maintenance"
        )
        payload = created.model_dump(exclude_none=True)
        self.assertEqual(
            payload["spec"]["affinity"]["node_label_selector"],
            "vmss=1,fabric,!maintenance",
        )

    def test_job_create_without_selector_omits_affinity(self):
        result = self._invoke([])
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertIsNone(created.spec.affinity)
        self.assertNotIn("affinity", created.model_dump(exclude_none=True)["spec"])

    def test_job_create_rejects_selector_with_node_id(self):
        result = self._invoke(
            ["--node-id", "node-1", "--node-label-selector", "vmss=1"]
        )
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("cannot be combined with --node-id", result.output)
        self.assertIsNone(_FakeAPIClient.last_instance.job.created_job)

    def test_job_create_rejects_empty_selector(self):
        result = self._invoke(["--node-label-selector", "   "])
        self.assertEqual(result.exit_code, 2, result.output)
        output = " ".join(result.output.split())
        self.assertIn("must not be empty or only whitespace", output)
        self.assertIsNone(_FakeAPIClient.last_instance)

    def test_file_selector_is_sent_and_cli_value_overrides_it(self):
        path = self._write_spec({"node_label_selector": "vmss=1"})
        kept = self._invoke([], spec_file=path)
        self.assertEqual(kept.exit_code, 0, kept.output)
        self.assertEqual(
            _FakeAPIClient.last_instance.job.created_job.spec.affinity.node_label_selector,
            "vmss=1",
        )

        overridden = self._invoke(
            ["--node-label-selector", "fabric=rdma"], spec_file=path
        )
        self.assertEqual(overridden.exit_code, 0, overridden.output)
        self.assertEqual(
            _FakeAPIClient.last_instance.job.created_job.spec.affinity.node_label_selector,
            "fabric=rdma",
        )

    def test_file_selector_conflicts_with_allowed_nodes(self):
        path = self._write_spec({
            "node_label_selector": "vmss=1",
            "allowed_nodes_in_node_group": ["node-1"],
        })
        result = self._invoke([], spec_file=path)
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("mutually exclusive", " ".join(result.output.split()))
        self.assertIsNone(_FakeAPIClient.last_instance.job.created_job)

    def test_node_group_keeps_file_selector(self):
        path = self._write_spec({"node_label_selector": "vmss=1"})
        _FakeAPIClient.last_instance = None
        with (
            patch("leptonai.cli.job.APIClient", _FakeAPIClient),
            patch("leptonai.cli.util._get_valid_nodegroup_ids", return_value=["ng-1"]),
        ):
            result = CliRunner().invoke(
                cli, _create_args("--file", path, "--node-group", "my-group")
            )
        self.assertEqual(result.exit_code, 0, result.output)
        affinity = _FakeAPIClient.last_instance.job.created_job.spec.affinity
        self.assertEqual(affinity.allowed_dedicated_node_groups, ["ng-1"])
        self.assertEqual(affinity.node_label_selector, "vmss=1")
        self.assertIsNone(affinity.allowed_nodes_in_node_group)

    def test_job_create_help_documents_node_label_selector(self):
        result = CliRunner().invoke(cli, ["job", "create", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        help_text = " ".join(result.output.split())
        self.assertIn("--node-label-selector", help_text)
        self.assertIn("Cannot be combined with --node-id", help_text)
