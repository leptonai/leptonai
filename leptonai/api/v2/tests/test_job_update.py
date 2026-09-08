import os
import tempfile
import json

import requests
import responses

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.job import JobAPI
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.job import LeptonJob


def _job_api() -> JobAPI:
    client = APIClient.__new__(APIClient)
    client.url = "https://workspace.example/api/v1"
    client._header = {}
    client._timeout = 120
    client._session = requests.Session()
    return JobAPI(client)


@responses.activate
def test_update_serializes_job_model():
    responses.patch(
        "https://workspace.example/api/v1/jobs/job-1",
        json={},
        status=200,
    )

    job = LeptonJob(metadata=Metadata(id="job-1"))

    assert _job_api().update("job-1", job)
    body = json.loads(responses.calls[0].request.body)
    assert body["metadata"]["id"] == "job-1"


@responses.activate
def test_update_preserves_partial_dict_payload():
    responses.patch(
        "https://workspace.example/api/v1/jobs/job-1",
        json={},
        status=200,
    )
    payload = {"spec": {"stopped": True}}

    assert _job_api().update("job-1", payload)
    assert json.loads(responses.calls[0].request.body) == payload
