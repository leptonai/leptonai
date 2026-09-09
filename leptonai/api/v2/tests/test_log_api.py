"""Unit tests for LogAPI.get_log's `direction` parameter.

These construct a LogAPI instance directly with a fake `_client` exposing a
mocked `_get`, avoiding a real HTTP call, and assert on the `params` dict
`_get` was called with -- i.e. the request shape LogAPI builds, not the
network layer itself.
"""

import os
import tempfile

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import unittest
from unittest.mock import MagicMock, patch

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.log import LogAPI, LogAPIError


class _FakeResponse:
    def __init__(self, payload, ok=True, status_code=200, text="", headers=None):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self):
        self.new_deployment_api_enabled = False
        self._get = MagicMock(return_value=_FakeResponse({"data": {"result": []}}))
        self._post = MagicMock()
        self._put = MagicMock()
        self._patch = MagicMock()
        self._delete = MagicMock()
        self._head = MagicMock()


class TestLogAPIDirection(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()
        self.log_api = LogAPI(self.client)

    def test_default_direction_is_backward(self):
        """Omitting `direction` preserves today's default."""
        self.log_api.get_log(name_or_deployment="dep-1", start=100, end=200)

        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertEqual(params["direction"], "backward")
        self.assertEqual(params["start"], 100)
        self.assertEqual(params["end"], 200)

    def test_explicit_forward_direction_is_honored(self):
        """explicit direction="forward" is sent through."""
        self.log_api.get_log(
            name_or_deployment="dep-1", start=100, end=200, direction="forward"
        )

        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertEqual(params["direction"], "forward")
        self.assertEqual(params["start"], 100)
        self.assertEqual(params["end"], 200)

    def test_explicit_backward_direction_is_honored(self):
        self.log_api.get_log(
            name_or_deployment="dep-1", start=100, end=200, direction="backward"
        )

        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertEqual(params["direction"], "backward")

    def test_start_end_are_passed_through_unchanged(self):
        """[start, end) request-shape regression: start/end are sent verbatim."""
        self.log_api.get_log(name_or_deployment="dep-1", start=12345, end=67890)

        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertEqual(params["start"], 12345)
        self.assertEqual(params["end"], 67890)


class TestLogAPITimeout(unittest.TestCase):
    """`get_log`'s optional `timeout` parameter, passed through to the
    underlying HTTP GET when provided and omitted (falling back to the
    client's own default) when not -- so existing callers that never pass
    `timeout` see unchanged behavior.
    """

    def setUp(self):
        self.client = _FakeClient()
        self.log_api = LogAPI(self.client)

    def test_timeout_omitted_by_default(self):
        self.log_api.get_log(name_or_deployment="dep-1", start=100, end=200)

        _, kwargs = self.client._get.call_args
        self.assertNotIn("timeout", kwargs)

    def test_explicit_timeout_is_passed_through(self):
        self.log_api.get_log(name_or_deployment="dep-1", start=100, end=200, timeout=30)

        _, kwargs = self.client._get.call_args
        self.assertEqual(kwargs["timeout"], 30)

    def test_explicit_timeout_does_not_affect_params(self):
        """`timeout` is a request-transport kwarg, not a query param."""
        self.log_api.get_log(name_or_deployment="dep-1", start=100, end=200, timeout=30)

        _, kwargs = self.client._get.call_args
        self.assertNotIn("timeout", kwargs["params"])


class TestLogAPITimeoutReachesTransport(unittest.TestCase):
    """Fix 2: closes the gap between "the `timeout` kwarg reaches
    `LogAPI.get_log`" (`TestLogAPITimeout` above, mocked at the `get_log`
    boundary) and "`get_log`'s actual HTTP request honors it". Mocks one
    level below `get_log` -- `requests.Session.get`, via a real `APIClient`
    (constructed with explicit credentials, so no env/login state or
    network I/O is involved) and a real `LogAPI` wrapping it -- so a
    regression that dropped `timeout` somewhere in `get_log` ->
    `self._get` -> `APIClient._get` -> `self._session.get` would be caught
    here even though it would not be caught by only asserting on `_get`.
    """

    def setUp(self):
        self.client = APIClient(
            workspace_id="test-workspace",
            auth_token="test-token",
            url="http://fake-workspace.example",
        )
        self.log_api = LogAPI(self.client)

    def test_timeout_reaches_the_underlying_session_get_call(self):
        fake_response = _FakeResponse({"data": {"result": []}})
        with patch.object(
            self.client._session, "get", return_value=fake_response
        ) as mock_get:
            self.log_api.get_log(
                name_or_deployment="dep-1", start=100, end=200, timeout=42
            )

        self.assertEqual(mock_get.call_count, 1)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["timeout"], 42)

    def test_timeout_omitted_falls_back_to_client_default_at_transport(self):
        fake_response = _FakeResponse({"data": {"result": []}})
        with patch.object(
            self.client._session, "get", return_value=fake_response
        ) as mock_get:
            self.log_api.get_log(name_or_deployment="dep-1", start=100, end=200)

        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["timeout"], self.client._timeout)


class TestLogAPIErrorContract(unittest.TestCase):
    """`get_log` raises structured `LogAPIError` for any
    non-2xx response, carrying `status_code`/`retry_after`; message text is
    byte-for-byte identical to the pre-existing bare-`RuntimeError` message.
    """

    def setUp(self):
        self.client = _FakeClient()
        self.log_api = LogAPI(self.client)

    def test_non_429_error_is_runtimeerror_compatible_with_identical_message(self):
        self.client._get.return_value = _FakeResponse(
            None, ok=False, status_code=500, text="internal error"
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        exc = cm.exception
        self.assertIsInstance(exc, RuntimeError)
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(
            str(exc), "API call failed with status code 500. Details: internal error"
        )

    def test_429_threads_status_code_and_retry_after(self):
        self.client._get.return_value = _FakeResponse(
            None,
            ok=False,
            status_code=429,
            text="rate limited",
            headers={"Retry-After": "10"},
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        exc = cm.exception
        self.assertEqual(exc.status_code, 429)
        self.assertEqual(exc.retry_after, 10.0)

    def test_429_without_retry_after_header_leaves_it_none(self):
        self.client._get.return_value = _FakeResponse(
            None, ok=False, status_code=429, text="rate limited", headers={}
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        self.assertIsNone(cm.exception.retry_after)

    def test_http_date_retry_after_is_treated_as_absent(self):
        """Only the delay-in-seconds form is parsed."""
        self.client._get.return_value = _FakeResponse(
            None,
            ok=False,
            status_code=429,
            text="rate limited",
            headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        self.assertIsNone(cm.exception.retry_after)

    def test_negative_retry_after_is_treated_as_absent(self):
        """A non-positive Retry-After is not a usable delay -- treated the
        same as an unparseable value, never passed through as a negative
        `retry_after`."""
        self.client._get.return_value = _FakeResponse(
            None,
            ok=False,
            status_code=429,
            text="rate limited",
            headers={"Retry-After": "-5"},
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        self.assertIsNone(cm.exception.retry_after)

    def test_zero_retry_after_is_treated_as_absent(self):
        self.client._get.return_value = _FakeResponse(
            None,
            ok=False,
            status_code=429,
            text="rate limited",
            headers={"Retry-After": "0"},
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        self.assertIsNone(cm.exception.retry_after)

    def test_positive_retry_after_still_parses(self):
        self.client._get.return_value = _FakeResponse(
            None,
            ok=False,
            status_code=429,
            text="rate limited",
            headers={"Retry-After": "3"},
        )
        with self.assertRaises(LogAPIError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=1, end=200)
        self.assertEqual(cm.exception.retry_after, 3.0)


class TestLogAPIEpochZeroRejected(unittest.TestCase):
    """`start=0`/`end=0` are explicitly rejected, never silently passed
    through to the /logs API or substituted with a default window."""

    def setUp(self):
        self.client = _FakeClient()
        self.log_api = LogAPI(self.client)

    def test_start_zero_with_valid_end_raises_and_makes_no_request(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1",
                start=0,
                end=1_000_000_000,
                direction="forward",
            )
        message = str(cm.exception)
        self.assertNotIn("both start or end must be specified", message)
        # The message must actually explain the epoch-zero/omitted
        # ambiguity, not merely avoid colliding with the sibling message.
        self.assertIn("cannot be distinguished", message)
        self.assertIn("omitted", message)
        self.client._get.assert_not_called()

    def test_end_zero_with_valid_start_raises_and_makes_no_request(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=5, end=0)
        message = str(cm.exception)
        self.assertNotIn("both start or end must be specified", message)
        self.assertIn("cannot be distinguished", message)
        self.assertIn("omitted", message)
        self.client._get.assert_not_called()

    def test_only_start_provided_raises(self):
        # Companion regression guard: the exactly-one-provided branch must
        # raise its own distinct message, not be conflated with the
        # epoch-zero rejection above.
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=5, end=None)
        message = str(cm.exception)
        self.assertIn("both start or end must be specified", message)
        self.assertNotIn("cannot be distinguished", message)
        self.client._get.assert_not_called()

    def test_only_end_provided_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=None, end=5)
        message = str(cm.exception)
        self.assertIn("both start or end must be specified", message)
        self.assertNotIn("cannot be distinguished", message)
        self.client._get.assert_not_called()

    def test_non_zero_start_and_end_are_not_rejected(self):
        """Control case: the `start == 0 or end == 0` guard must only fire
        on a literal zero, not on any other falsy-adjacent small value."""
        self.log_api.get_log(
            name_or_deployment="dep-1",
            start=1,
            end=1_000_000_000,
            direction="forward",
        )
        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertEqual(params["start"], 1)
        self.assertEqual(params["end"], 1_000_000_000)
        self.assertIn("direction", params)
        self.assertIn("limit", params)
        self.assertIn("q", params)
        self.assertIn("job_query_mode", params)

    def test_neither_provided_omits_time_range_params(self):
        self.log_api.get_log(name_or_deployment="dep-1")
        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertNotIn("start", params)
        self.assertNotIn("end", params)


class TestLogAPIEndAfterStartAndNegativeRejected(unittest.TestCase):
    """`end <= start` and negative `start`/`end` timestamps are rejected as
    clear client-side errors, without changing the `start`/`end` type
    annotation (both remain `str`).
    """

    def setUp(self):
        self.client = _FakeClient()
        self.log_api = LogAPI(self.client)

    def test_end_equal_start_int_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start=1_000_000_000, end=1_000_000_000
            )
        self.assertIn("end must be after start", str(cm.exception))
        self.client._get.assert_not_called()

    def test_end_before_start_int_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start=1_000_000_000, end=500_000_000
            )
        self.assertIn("end must be after start", str(cm.exception))
        self.client._get.assert_not_called()

    def test_end_before_start_string_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start="1000000000", end="500000000"
            )
        self.assertIn("end must be after start", str(cm.exception))
        self.client._get.assert_not_called()

    def test_negative_start_int_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start=-1, end=1_000_000_000
            )
        self.assertIn("non-negative", str(cm.exception))
        self.client._get.assert_not_called()

    def test_negative_start_string_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start="-1", end="1000000000"
            )
        self.assertIn("non-negative", str(cm.exception))
        self.client._get.assert_not_called()

    def test_negative_end_int_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start=1_000_000_000, end=-1
            )
        self.assertIn("non-negative", str(cm.exception))
        self.client._get.assert_not_called()

    def test_negative_end_string_form_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(
                name_or_deployment="dep-1", start="1000000000", end="-1"
            )
        self.assertIn("non-negative", str(cm.exception))
        self.client._get.assert_not_called()

    def test_negative_single_sided_start_raises_before_both_required_error(self):
        # Only `start` provided (negative) -- the negative check must fire
        # before the "both must be specified" mismatch check.
        with self.assertRaises(RuntimeError) as cm:
            self.log_api.get_log(name_or_deployment="dep-1", start=-1, end=None)
        message = str(cm.exception)
        self.assertIn("non-negative", message)
        self.assertNotIn("both start or end must be specified", message)
        self.client._get.assert_not_called()

    def test_valid_ascending_non_negative_non_zero_pair_succeeds(self):
        """Control case: an ordinary valid range is not over-tightened."""
        self.log_api.get_log(
            name_or_deployment="dep-1", start=1_000_000_000, end=2_000_000_000
        )
        _, kwargs = self.client._get.call_args
        params = kwargs["params"]
        self.assertEqual(params["start"], 1_000_000_000)
        self.assertEqual(params["end"], 2_000_000_000)


if __name__ == "__main__":
    unittest.main()
