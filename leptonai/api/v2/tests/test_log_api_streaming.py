"""Shared /logs contract, including the backend's replica + empty-q mode switch."""

import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.log import LogAPI, LogAPIError

BASE = "https://logs.example/api/v2/workspaces/ws"


def client():
    return APIClient(workspace_id="ws", auth_token="test", url=BASE)


@pytest.mark.parametrize(
    "method,route", [("get_log", "/logs"), ("get_log_time_series", "/logs/timeseries")]
)
@pytest.mark.parametrize(
    "scope,expected",
    [
        (
            {"name_or_endpoint": "ep", "component": "worker"},
            {"endpoint": "ep", "component": "worker"},
        ),
        ({"name_or_dev_pod": "dev"}, {"dev_pod": "dev"}),
        ({"name_or_dynamo": "dyn"}, {"dynamo_graph_deployment": "dyn"}),
        (
            {
                "name_or_ray_cluster": "ray",
                "ray_job_id": "j",
                "ray_node_id": "n",
                "ray_component": "worker",
            },
            {
                "ray_cluster": "ray",
                "ray_job_id": "j",
                "ray_node_id": "n",
                "ray_component": "worker",
            },
        ),
        (
            {
                "slurm_namespace": "ns",
                "slurm_cluster": "sc",
                "slurm_host": "h",
                "slurm_node": "n",
                "slurm_job": "1",
                "slurm_step": "2",
                "slurm_attempt": "0",
                "slurm_log_type": "stdout",
            },
            {
                "slurm_namespace": "ns",
                "slurm_cluster": "sc",
                "slurm_host": "h",
                "slurm_node": "n",
                "slurm_job": "1",
                "slurm_step": "2",
                "slurm_attempt": "0",
                "slurm_log_type": "stdout",
            },
        ),
    ],
)
@responses.activate
def test_historical_filters_without_time_bounds(method, route, scope, expected):
    payload = {"data": {"result": []}}
    responses.get(BASE + route, json=payload)
    assert (
        getattr(client().log, method)(
            **scope,
            q="error & detail",
            level="error,warn",
            limit=12,
            direction="forward",
            job_query_mode="archive_only",
        )
        == payload
    )
    query = parse_qs(urlparse(responses.calls[-1].request.url).query)
    expected.update(
        q="error & detail",
        level="error,warn",
        limit="12",
        direction="forward",
        job_query_mode="archive_only",
    )
    for key, value in expected.items():
        assert query[key] == [value]
    assert not {"stream", "self", "timeout", "start", "end"}.intersection(query)


@pytest.mark.parametrize("bounds", [{"start": 1}, {"end": 123}, {"start": 1, "end": 2}])
@responses.activate
def test_independent_time_bounds(bounds):
    responses.get(BASE + "/logs", json={})
    client().log.get_log(name_or_job="job", **bounds)
    query = parse_qs(urlparse(responses.calls[-1].request.url).query)
    for key, value in bounds.items():
        assert query[key] == [str(value)]
    for missing in {"start", "end"} - bounds.keys():
        assert missing not in query


@pytest.mark.parametrize(
    "options",
    [
        {"stream": True},
        {"stream": True, "replica": "r", "start": 1},
        {"stream": True, "replica": "r", "end": 2},
        {"stream": True, "replica": "r", "level": "error"},
        {"stream": True, "replica": "r", "limit": 20},
        {"stream": True, "replica": "r", "direction": "forward"},
        {
            "stream": True,
            "replica": "r",
            "slurm_namespace": "ns",
            "slurm_cluster": "sc",
        },
        {"name_or_job": "j", "name_or_dev_pod": "dev"},
        {"ray_job_id": "j"},
        {"component": "c"},
        {"slurm_cluster": "sc"},
        {"job_history_name": "gen1"},
        {"direction": "sideways"},
        {"limit": 0},
        {"job_query_mode": "invalid"},
    ],
)
def test_invalid_combinations_fail_before_request(options):
    fake = Mock()
    with pytest.raises(ValueError):
        LogAPI(fake).get_log(**options)
    fake._get.assert_not_called()


@responses.activate
def test_historical_replica_with_query_and_job_generation():
    responses.get(BASE + "/logs", json={})
    client().log.get_log(
        name_or_job="job", replica="old-pod", q="error", job_history_name="job-gen1"
    )
    query = parse_qs(urlparse(responses.calls[-1].request.url).query)
    assert query["job"] == ["job"]
    assert query["job_history_name"] == ["job-gen1"]
    assert query["replica"] == ["old-pod"]


@responses.activate
def test_slurm_replica_does_not_select_live_mode():
    responses.get(BASE + "/logs", json={"data": {"result": []}})
    result = client().log.get_log(slurm_namespace="ns", slurm_cluster="sc", replica="r")
    assert isinstance(result, dict)


def fake_response(content_type="text/plain", status=200):
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = content_type
    response._content = b'{"message":"denied"}'
    response.close = Mock()
    return response


@pytest.mark.parametrize("failure", ["http", "json", "disconnect", "close"])
def test_stream_closes_response_on_all_exit_paths(failure):
    response = fake_response(
        "application/json" if failure == "json" else "text/plain",
        403 if failure == "http" else 200,
    )

    def chunks(**kwargs):
        yield b"first\n"
        raise requests.ConnectionError("disconnected")

    response.iter_content = chunks
    fake = Mock()
    fake._get.return_value = response
    stream = LogAPI(fake).get_log(name_or_endpoint="ep", replica="r", stream=True)
    if failure == "http":
        with pytest.raises(LogAPIError):
            next(stream)
    elif failure == "json":
        with pytest.raises(RuntimeError, match="returned JSON"):
            next(stream)
    elif failure == "disconnect":
        assert next(stream) == "first\n"
        with pytest.raises(requests.ConnectionError):
            next(stream)
    else:
        assert next(stream) == "first\n"
        stream.close()
    response.close.assert_called_once()


def test_json_mode_rejects_unexpected_text_without_reading_body():
    response = fake_response()
    response.json = Mock(side_effect=AssertionError("must not read a live body"))
    fake = Mock()
    fake._get.return_value = response
    with pytest.raises(RuntimeError, match="live logs"):
        LogAPI(fake).get_log(name_or_endpoint="ep")
    response.json.assert_not_called()
    response.close.assert_called_once()


@pytest.mark.parametrize("query_options", [{}, {"q": ""}, {"q": "ignored"}])
def test_real_http_stream_yields_before_eof_and_decodes_split_unicode(query_options):
    release = threading.Event()
    finished = threading.Event()
    queries = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            queries.append(parse_qs(urlparse(self.path).query, keep_blank_values=True))
            # Deployed servers can treat even q= as a historical query. Model
            # that wire-level distinction instead of always returning text.
            if "q" in queries[-1]:
                body = b'{"data":{"result":[]}}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                finished.set()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def send(data):
                self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
                self.wfile.flush()

            try:
                send(b"first\n")
                release.wait(5)
                encoded = "你好\n".encode()
                send(encoded[:1])
                send(encoded[1:4])
                send(encoded[4:])
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            finally:
                finished.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    api_client = APIClient(
        workspace_id="ws",
        auth_token="test",
        url=f"http://127.0.0.1:{server.server_port}",
    )
    stream = api_client.log.get_log(
        name_or_endpoint="ep",
        replica="r",
        stream=True,
        timestamps=True,
        timeout=2,
        **query_options,
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(next, stream)
            try:
                assert future.result(timeout=2) == "first\n"
                assert not finished.is_set(), "The caller must receive logs before EOF"
            finally:
                release.set()
        assert "".join(stream) == "你好\n"
        assert queries[0]["timestamps"] == ["true"]
        assert queries[0]["replica"] == ["r"]
        assert "q" not in queries[0]
        assert not {"stream", "start", "end", "limit", "direction"}.intersection(
            queries[0]
        )
    finally:
        release.set()
        stream.close()
        api_client._session.close()
        server.shutdown()
        server.server_close()
        thread.join(2)


@pytest.mark.parametrize("timestamps", [True, False])
def test_stream_timeout_and_timestamps_are_transport_and_query_options(timestamps):
    response = fake_response()
    response.iter_content = Mock(return_value=iter([b"first\n"]))
    fake = Mock()
    fake._get.return_value = response
    assert list(
        LogAPI(fake).get_log(
            name_or_job="job",
            replica="r",
            stream=True,
            timeout=7,
            timestamps=timestamps,
        )
    ) == ["first\n"]
    kwargs = fake._get.call_args.kwargs
    assert kwargs["timeout"] == 7
    assert kwargs["stream"] is True
    assert kwargs["params"]["timestamps"] == str(timestamps).lower()
    assert "timeout" not in kwargs["params"]
    response.close.assert_called_once()


@responses.activate
def test_timeseries_explicit_query_and_transport_parameters():
    responses.get(BASE + "/logs/timeseries", json={"data": {"result": []}})
    api_client = client()
    from unittest.mock import patch

    with patch.object(api_client._session, "get", wraps=api_client._session.get) as get:
        api_client.log.get_log_time_series(
            name_or_endpoint="ep",
            component="worker",
            replica="r",
            start=10,
            end=20,
            interval_ms=1000,
            limit=12,
            q="error",
            level="warn,error",
            direction="forward",
            job_query_mode="alive_only",
            timeout=3,
        )
    query = parse_qs(urlparse(responses.calls[-1].request.url).query)
    assert query == {
        "endpoint": ["ep"],
        "component": ["worker"],
        "replica": ["r"],
        "start": ["10"],
        "end": ["20"],
        "interval_ms": ["1000"],
        "limit": ["12"],
        "q": ["error"],
        "level": ["warn,error"],
        "direction": ["forward"],
        "job_query_mode": ["alive_only"],
    }
    assert get.call_args.kwargs["timeout"] == 3


@pytest.mark.parametrize(
    "options,message",
    [
        ({"name_or_dynamo": "dyn", "dynamo_service": "worker"}, "dynamo_service"),
        ({"name_or_dev_pod": "dev", "replica": "r"}, "replica filtering for DevPods"),
    ],
)
def test_timeseries_rejects_filters_ignored_by_backend(options, message):
    fake = Mock()
    with pytest.raises(ValueError, match=message):
        LogAPI(fake).get_log_time_series(**options)
    fake._get.assert_not_called()


@pytest.mark.parametrize(
    "query_options,expected",
    [
        ({}, ""),
        ({"q": ""}, ""),
        ({"q": None}, ""),
        ({"q": "error & detail"}, "error & detail"),
    ],
)
@pytest.mark.parametrize("bounds", [{}, {"start": 1, "end": 2}])
@responses.activate
def test_historical_replica_always_sends_query(query_options, expected, bounds):
    payload = {"data": {"result": []}}
    responses.get(BASE + "/logs", json=payload)
    assert (
        client().log.get_log(
            name_or_endpoint="ep", replica="r", **query_options, **bounds
        )
        == payload
    )
    query = parse_qs(
        urlparse(responses.calls[-1].request.url).query, keep_blank_values=True
    )
    assert query["q"] == [expected]
    assert query["replica"] == ["r"]
