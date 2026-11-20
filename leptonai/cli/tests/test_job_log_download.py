import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
os.environ["LEPTON_CACHE_DIR"] = tempfile.mkdtemp()

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner
from requests import RequestException

from leptonai.api.v2.log_export import LogExportAPIError
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.job import LeptonJob, LeptonJobStatus
from leptonai.api.v2.types.log_export import LogExport
from leptonai.cli import lep as cli
from leptonai.cli import log_export


JOB_UID = "11111111-1111-4111-8111-111111111111"
EXPORT_ID = "0123456789abcdef0123456789abcdef"


def _export(state, **extra):
    body = {
        "id": EXPORT_ID,
        "state": state,
        "workload": {"kind": "job", "id": "job-1", "uid": JOB_UID},
        "start": "2026-10-19T12:00:00Z",
        "end": "2026-10-19T12:05:00Z",
        "format": "ndjson",
        "filters": {"replicas": [], "containers": [], "levels": [], "contains": ""},
        "warnings": [],
        **extra,
    }
    return LogExport(**body)


def _api_error(status, reason=None, export_id=None, retry_after=None, **details):
    response = SimpleNamespace(
        status_code=status,
        reason="Error",
        headers={"Retry-After": str(retry_after)} if retry_after else {},
    )
    body = {
        "code": "Error",
        "message": "boom",
        "details": {
            k: v
            for k, v in {"reason": reason, "export_id": export_id, **details}.items()
            if v is not None
        },
    }
    return LogExportAPIError(response, body)


class _Download:
    def __init__(self, chunks, error=None):
        self._chunks = chunks
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, chunk_size=None):
        yield from self._chunks
        if self._error:
            raise self._error


def _client(
    create=True, access=True, job_uuid=JOB_UID, states=("RUNNING", "COMPLETED")
):
    client = Mock()
    client.workspace_id = "ws-1"
    client.info.return_value = SimpleNamespace(
        features=SimpleNamespace(
            enable_log_exports_create=create, enable_log_exports_access=access
        )
    )
    client.job.get.return_value = LeptonJob(
        metadata=Metadata(id="job-1", uuid=job_uuid),
        status=LeptonJobStatus(
            creation_time=int(
                datetime(2026, 10, 19, 12, tzinfo=timezone.utc).timestamp() * 1000
            ),
            completion_time=int(
                datetime(2026, 10, 19, 12, 5, tzinfo=timezone.utc).timestamp() * 1000
            ),
        ),
    )
    client.log_export.create.return_value = (_export("RUNNING"), None)
    client.log_export.get.side_effect = [(_export(s), None) for s in states]
    client.log_export.download.return_value = _Download([b'{"a":1}\n', b'{"b":2}\n'])
    return client


class TestJobDownloadLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.output = os.path.join(self.tmp, "logs.ndjson")
        sleep = patch("leptonai.cli.log_export.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def _invoke(self, client, *args):
        with patch("leptonai.cli.job.APIClient", return_value=client):
            result = CliRunner().invoke(cli, ["job", "log", "download", *args])
        # Rich wraps long lines; compare messages with whitespace collapsed.
        result.text = " ".join(result.output.split())
        return result

    def test_creates_waits_and_saves_file(self):
        client = _client()
        result = self._invoke(
            client, "-i", "job-1", "-r", "job-1-0", "--contains", "err", "-o",
            self.output,
        )  # fmt: skip
        self.assertEqual(result.exit_code, 0, result.output)
        with open(self.output, "rb") as f:
            self.assertEqual(f.read(), b'{"a":1}\n{"b":2}\n')
        self.assertFalse(os.path.exists(self.output + ".part"))

        request, key = client.log_export.create.call_args.args
        self.assertEqual(request.workload.kind, "job")
        self.assertEqual(request.workload.id_, "job-1")
        self.assertEqual(request.workload.uid, JOB_UID)
        # Defaults come from the job's lifetime; completion rounds up a second.
        self.assertEqual(request.start, "2026-10-19T12:00:00Z")
        self.assertEqual(request.end, "2026-10-19T12:05:01Z")
        self.assertEqual(request.filters.replicas, ["job-1-0"])
        self.assertEqual(request.filters.contains, "err")
        self.assertTrue(key)
        client.job.get.assert_called_once_with("job-1", job_query_mode="alive_only")

    def test_request_serializes_with_api_field_names(self):
        client = _client()
        self._invoke(client, "-i", "job-1", "-o", self.output)
        request, _ = client.log_export.create.call_args.args
        body = request.dict(by_alias=True)
        self.assertEqual(
            body["workload"], {"kind": "job", "id": "job-1", "uid": JOB_UID}
        )
        self.assertEqual(body["format"], "ndjson")

    def test_create_disabled_fails_before_any_export_call(self):
        client = _client(create=None)
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Log download is not enabled for workspace ws-1", result.text)
        client.job.get.assert_not_called()
        client.log_export.create.assert_not_called()

    def test_access_disabled_blocks_resume(self):
        client = _client(create=True, access=False)
        result = self._invoke(client, "--export-id", EXPORT_ID, "-o", self.output)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("existing log exports is not enabled", result.text)
        client.log_export.get.assert_not_called()

    def test_older_server_without_features_is_disabled(self):
        client = _client()
        client.info.return_value = SimpleNamespace(features=None)
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertIn("not enabled", result.text)
        client.log_export.create.assert_not_called()

    def test_resume_downloads_existing_export(self):
        client = _client(create=False, states=("COMPLETED",))
        result = self._invoke(client, "--export-id", EXPORT_ID, "-o", self.output)
        self.assertEqual(result.exit_code, 0, result.output)
        client.log_export.create.assert_not_called()
        self.assertTrue(os.path.exists(self.output))

    def test_requires_exactly_one_target(self):
        client = _client()
        self.assertEqual(self._invoke(client).exit_code, 2)
        result = self._invoke(client, "-i", "job-1", "--export-id", EXPORT_ID)
        self.assertEqual(result.exit_code, 2)
        result = self._invoke(client, "--export-id", EXPORT_ID, "-r", "x")
        self.assertEqual(result.exit_code, 2)

    def test_missing_job_uid_is_reported(self):
        client = _client(job_uuid=None)
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertIn("did not return this job's UID", result.text)
        client.log_export.create.assert_not_called()

    def test_retries_busy_server_with_same_key(self):
        client = _client()
        client.log_export.create.side_effect = [
            _api_error(429, "export_capacity_exceeded", retry_after=5),
            (_export("RUNNING"), None),
        ]
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertEqual(result.exit_code, 0, result.output)
        first, second = client.log_export.create.call_args_list
        self.assertEqual(first.args, second.args)
        log_export.time.sleep.assert_any_call(5.0)

    def test_uncertain_submission_tracks_export_without_resubmitting(self):
        client = _client(states=("COMPLETED",))
        client.log_export.create.side_effect = _api_error(
            503, "export_submission_unknown", export_id=EXPORT_ID, retry_after=5
        )
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertEqual(result.exit_code, 0, result.output)
        client.log_export.create.assert_called_once()
        client.log_export.get.assert_called_with(EXPORT_ID)

    def test_submission_unknown_state_stops_with_resume_hint(self):
        client = _client(states=("SUBMISSION_UNKNOWN",))
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn(f"--export-id {EXPORT_ID}", result.text)

    def test_unsupported_range_shows_available_window(self):
        client = _client()
        client.log_export.create.side_effect = _api_error(
            400,
            "unsupported_range",
            available_start="2026-10-18T12:05:00Z",
            available_end="2026-10-19T12:05:00Z",
            max_range_seconds="86400",
        )
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("2026-10-18T12:05:00Z", result.text)
        self.assertIn("86400", result.text)

    def test_failed_export_reports_reason(self):
        client = _client()
        client.log_export.get.side_effect = [(
            _export(
                "FAILED",
                failure={"reason": "upstream_extraction_failed", "message": "x"},
            ),
            None,
        )]
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("upstream_extraction_failed", result.text)
        client.log_export.download.assert_not_called()

    def test_interrupted_download_leaves_no_file(self):
        client = _client()
        client.log_export.download.return_value = _Download(
            [b"partial"], RequestException("Response ended prematurely")
        )
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Download interrupted after 7 bytes", result.text)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_refuses_to_overwrite_existing_output(self):
        open(self.output, "w").close()
        client = _client(states=("COMPLETED",))
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertIn("already exists", result.text)
        client.log_export.download.assert_not_called()

    def test_no_wait_only_creates(self):
        client = _client()
        result = self._invoke(client, "-i", "job-1", "--no-wait")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(f"--export-id {EXPORT_ID}", result.text)
        client.log_export.get.assert_not_called()

    def test_default_window_is_capped_at_24_hours(self):
        client = _client()
        client.job.get.return_value.status = LeptonJobStatus(
            creation_time=int(
                datetime(2026, 10, 10, tzinfo=timezone.utc).timestamp() * 1000
            ),
            completion_time=int(
                datetime(2026, 10, 19, tzinfo=timezone.utc).timestamp() * 1000
            ),
        )
        result = self._invoke(client, "-i", "job-1", "-o", self.output)
        self.assertEqual(result.exit_code, 0, result.output)
        request, _ = client.log_export.create.call_args.args
        self.assertEqual(request.start, "2026-10-18T00:00:01Z")
        self.assertEqual(request.end, "2026-10-19T00:00:01Z")
        self.assertIn("last 24 hours", result.text)


class TestJobLogGroup(unittest.TestCase):
    def _invoke(self, client, *args):
        with patch("leptonai.cli.job.APIClient", return_value=client):
            return CliRunner().invoke(cli, ["job", "log", *args])

    def test_log_without_subcommand_still_streams(self):
        client = Mock()
        client.job.get_log.return_value = iter(["line 1\n"])
        result = self._invoke(client, "-i", "job-1", "-r", "job-1-0")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("line 1", result.output)
        client.job.get_log.assert_called_once_with(id_or_job="job-1", replica="job-1-0")

    def test_log_without_id_is_usage_error(self):
        result = self._invoke(Mock())
        self.assertEqual(result.exit_code, 2)
        self.assertIn("--id", result.output)

    def test_group_options_before_subcommand_are_rejected(self):
        client = Mock()
        result = self._invoke(client, "-i", "job-1", "download")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("lep job log download --id", " ".join(result.output.split()))
        client.log_export.create.assert_not_called()

    def test_help_lists_download(self):
        result = self._invoke(Mock(), "--help")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("download", result.output)


if __name__ == "__main__":
    unittest.main()
