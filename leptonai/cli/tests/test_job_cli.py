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


def _create_args(*extra, node_group="ng-1"):
    node_group_args = ["--node-group", node_group] if node_group else []
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
        *node_group_args,
        *extra,
    ]


class _NodeGroupLookupMixin:
    """Skip the node group lookup API; every name is treated as a valid id."""

    def setUp(self):
        patcher = patch(
            "leptonai.cli.util._get_valid_nodegroup_ids",
            side_effect=lambda names, **_: list(names),
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class TestJobCliStorageAttachment(_NodeGroupLookupMixin, unittest.TestCase):
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


def _job(name, *, state="Running", created_by="alice@example.com"):
    return LeptonJob(
        metadata=Metadata(id=name, name=name, created_by=created_by),
        status={"state": state},
    )


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
        # LEP-7612: archived listing fetches one capped page, not every page.
        self.assertEqual(kwargs["page"], 1)
        self.assertEqual(kwargs["page_size"], 500)
        self.assertIn("No jobs match the specified filters.", result.output)
        self.assertNotIn("full user id", result.output)

    def test_job_list_include_archived_warns_when_capped(self):
        jobs = [_job(f"j{i}") for i in range(500)]
        result, _, shown = self._invoke_with_table(["-ia"], jobs)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(shown), 500)
        self.assertIn("Showing the newest 500 matching jobs only.", result.output)

    def test_job_list_rejects_repeated_search(self):
        # LEP-7560: a repeated --search used to keep only the last value.
        result, list_all = self._invoke(["-q", "a", "-q", "b"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("can be given only once", result.output)
        list_all.assert_not_called()

    def test_job_list_accepts_shared_filter_names(self):
        result, list_all = self._invoke(
            ["--status", "Running", "--created-by", "alice", "--search", "train"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        kwargs = list_all.call_args.kwargs
        self.assertEqual(kwargs["status"], ["Running"])
        self.assertEqual(kwargs["created_by"], ["alice"])
        self.assertEqual(kwargs["q"], "train")

    def test_job_list_keeps_legacy_filter_names(self):
        result, list_all = self._invoke(
            ["--state", "Running", "--user", "alice", "--name-or-id", "train"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        kwargs = list_all.call_args.kwargs
        self.assertEqual(kwargs["status"], ["Running"])
        self.assertEqual(kwargs["created_by"], ["alice"])
        self.assertEqual(kwargs["q"], "train")
        result, list_all = self._invoke(["-q", "train"])
        self.assertEqual(list_all.call_args.kwargs["q"], "train")

    def _invoke_with_table(self, args, jobs):
        with patch("leptonai.cli.job._display_jobs_table") as table:
            result, list_all = self._invoke(args, jobs)
        shown = table.call_args.args[0] if table.call_args else []
        return result, list_all, [j.metadata.name for j in shown]

    def test_job_list_passes_state_and_user_through_unchanged(self):
        # The dashboard sends status/created_by to the server and shows what it
        # returns; the CLI must not re-filter (LEP-7575/7566).
        jobs = [
            _job("a", state="Starting"),
            _job("b", state="Restarting", created_by="malice@example.com"),
        ]
        result, list_all, shown = self._invoke_with_table(
            ["-s", "starting", "-u", "alice"], jobs
        )
        self.assertEqual(result.exit_code, 0, result.output)
        kwargs = list_all.call_args.kwargs
        self.assertEqual(kwargs["status"], ["Starting"])
        self.assertEqual(kwargs["created_by"], ["alice"])
        self.assertEqual(shown, ["a", "b"])

    def test_job_list_state_rejects_values_the_dashboard_does_not_offer(self):
        result, list_all = self._invoke(["-s", "run"])
        self.assertEqual(result.exit_code, 2)
        list_all.assert_not_called()
        result, list_all = self._invoke(["-s", "PendingRetry"])
        self.assertEqual(result.exit_code, 2)

    def test_job_list_allows_state_with_include_archived(self):
        result, list_all = self._invoke(["-ia", "-s", "deleted"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(list_all.call_args.kwargs["status"], ["Deleted"])

    def test_job_list_state_help_is_derived_from_the_enum(self):
        result = CliRunner().invoke(cli, ["job", "list", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Terminating", result.output)
        self.assertIn("-l, --label", result.output)


class TestJobCreateNodeLabelSelector(_NodeGroupLookupMixin, unittest.TestCase):
    def _invoke(self, extra, spec_file=None):
        _FakeAPIClient.last_instance = None
        # A spec file carries its own node group, so no --node-group flag.
        args = _create_args(*extra, node_group=None if spec_file else "ng-1")
        if spec_file is not None:
            args.extend(["--file", spec_file])
        with patch("leptonai.cli.job.APIClient", _FakeAPIClient):
            result = CliRunner().invoke(cli, args)
        return result

    def _write_spec(self, affinity):
        affinity = {"allowed_dedicated_node_groups": ["ng-file"], **affinity}
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

    def test_job_create_without_selector_only_sends_node_group(self):
        result = self._invoke([])
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertEqual(
            created.model_dump(exclude_none=True)["spec"]["affinity"],
            {"allowed_dedicated_node_groups": ["ng-1"]},
        )

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

    def test_blank_file_selector_is_dropped(self):
        path = self._write_spec({
            "node_label_selector": "   ",
            "allowed_nodes_in_node_group": ["node-1"],
        })
        result = self._invoke([], spec_file=path)
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertEqual(
            created.model_dump(exclude_none=True)["spec"]["affinity"],
            {
                "allowed_dedicated_node_groups": ["ng-file"],
                "allowed_nodes_in_node_group": ["node-1"],
            },
        )

    def test_node_group_keeps_file_selector(self):
        path = self._write_spec({"node_label_selector": "vmss=1"})
        result = self._invoke(["--node-group", "my-group"], spec_file=path)
        self.assertEqual(result.exit_code, 0, result.output)
        affinity = _FakeAPIClient.last_instance.job.created_job.spec.affinity
        self.assertEqual(affinity.allowed_dedicated_node_groups, ["my-group"])
        self.assertEqual(affinity.node_label_selector, "vmss=1")
        self.assertIsNone(affinity.allowed_nodes_in_node_group)

    def test_job_create_help_documents_node_label_selector(self):
        result = CliRunner().invoke(cli, ["job", "create", "--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        help_text = " ".join(result.output.split())
        self.assertIn("--node-label-selector", help_text)
        self.assertIn("Cannot be combined with --node-id", help_text)


class TestJobCreateRequiresNodeGroup(_NodeGroupLookupMixin, unittest.TestCase):
    def _invoke(self, args):
        _FakeAPIClient.last_instance = None
        with patch("leptonai.cli.job.APIClient", _FakeAPIClient):
            return CliRunner().invoke(cli, args)

    def test_job_create_without_node_group_fails(self):
        result = self._invoke(_create_args(node_group=None))
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("Missing option '--node-group'", result.output)
        self.assertIsNone(_FakeAPIClient.last_instance.job.created_job)

    def test_spec_file_without_node_group_fails(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"resource_shape": config.DEFAULT_RESOURCE_SHAPE}, f)
        self.addCleanup(os.remove, f.name)
        result = self._invoke(_create_args("--file", f.name, node_group=None))
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("Missing option '--node-group'", result.output)
        self.assertIsNone(_FakeAPIClient.last_instance.job.created_job)

    def test_spec_file_node_group_satisfies_requirement(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "resource_shape": config.DEFAULT_RESOURCE_SHAPE,
                    "affinity": {"allowed_dedicated_node_groups": ["ng-file"]},
                },
                f,
            )
        self.addCleanup(os.remove, f.name)
        result = self._invoke(_create_args("--file", f.name, node_group=None))
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.job.created_job
        self.assertEqual(
            created.spec.affinity.allowed_dedicated_node_groups, ["ng-file"]
        )


if __name__ == "__main__":
    unittest.main()
