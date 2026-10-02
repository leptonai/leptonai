import json
from types import SimpleNamespace

from requests import Response

from leptonai.api.v2.job import JobAPI


def _response(payload):
    response = Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    response.headers["Content-Type"] = "application/json"
    return response


def _resource_client(get):
    return SimpleNamespace(
        _get=get,
        _post=lambda *args, **kwargs: None,
        _put=lambda *args, **kwargs: None,
        _patch=lambda *args, **kwargs: None,
        _delete=lambda *args, **kwargs: None,
        _head=lambda *args, **kwargs: None,
    )


def test_list_matching_decodes_enveloped_job_response():
    calls = []

    def get(path, **kwargs):
        calls.append((path, kwargs))
        return _response({"jobs": [{"metadata": {"id": "job-123"}}]})

    jobs = JobAPI(_resource_client(get)).list_matching("team=platform")

    assert [job.metadata.id_ for job in jobs] == ["job-123"]
    assert calls == [("/jobs", {"params": {"query": "team=platform"}})]
