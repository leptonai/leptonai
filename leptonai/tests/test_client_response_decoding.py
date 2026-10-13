"""Regression coverage for Client response decoding."""

from __future__ import annotations

from typing import Optional

import httpx
import pytest
import respx

from leptonai.client import Client

BASE_URL = "https://deployment.example"
TOKEN = "test-token"


def _mock_handshake() -> None:
    """Mock the endpoints that Client.__init__ calls while constructing."""
    respx.get(f"{BASE_URL}/healthz").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"status": "ok"},
        )
    )
    respx.get(f"{BASE_URL}/openapi.json").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"paths": {}},
        )
    )


@pytest.fixture
def make_client():
    """Build a fully constructed Client through the real Client.__init__."""
    clients = []

    def _make(stream: Optional[bool] = None) -> Client:
        _mock_handshake()
        client = Client(BASE_URL, token=TOKEN, stream=stream)
        clients.append(client)
        return client

    yield _make

    for client in clients:
        client._session.close()


@respx.mock
def test_client_construction_uses_real_init(make_client) -> None:
    """The fixture exercises Client.__init__, not a hand-built instance."""
    client = make_client(stream=None)

    assert client.url == BASE_URL
    assert client._session.headers["authorization"] == f"Bearer {TOKEN}"
    assert client.openapi == {"paths": {}}
    assert client._debug_record == []


@pytest.mark.parametrize("stream", [False, True])
@respx.mock
def test_json_content_type_parameters_decode_json(make_client, stream: bool) -> None:
    """Decode JSON despite charset parameters in buffered and stream modes."""
    respx.get(f"{BASE_URL}/json").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "application/json; charset=utf-8"},
            json={"ok": True},
        )
    )
    client = make_client(stream=stream)

    result = client._get_proper_res_content(client._get("json"))

    assert result == {"ok": True}


@pytest.mark.parametrize("content_type", ["APPLICATION/JSON", "application/JSON ;q=1"])
@respx.mock
def test_json_content_type_is_case_insensitive(make_client, content_type: str) -> None:
    """Media types are compared case-insensitively, as RFC 9110 requires."""
    respx.get(f"{BASE_URL}/case").mock(
        return_value=httpx.Response(
            200, headers={"content-type": content_type}, json={"cased": True}
        )
    )
    client = make_client(stream=False)

    assert client._get_proper_res_content(client._get("case")) == {"cased": True}


@respx.mock
def test_exact_json_content_type_decodes_json(make_client) -> None:
    """Decode an exact application/json buffered response through Client._get."""
    respx.get(f"{BASE_URL}/exact").mock(
        return_value=httpx.Response(
            200, headers={"content-type": "application/json"}, json={"exact": True}
        )
    )
    client = make_client(stream=False)

    assert client._get_proper_res_content(client._get("exact")) == {"exact": True}


@respx.mock
def test_buffered_binary_content_is_preserved(make_client) -> None:
    """Return a buffered binary success body through Client._get."""
    respx.get(f"{BASE_URL}/buffered").mock(
        return_value=httpx.Response(200, content=b"bytes")
    )
    client = make_client(stream=False)

    assert client._get_proper_res_content(client._get("buffered")) == b"bytes"


@pytest.mark.parametrize("content_type", [None, "image/png"])
@respx.mock
def test_streamed_non_chunked_binary_is_read(
    make_client, content_type: Optional[str]
) -> None:
    """Return a buffered binary body for streamed non-chunked success responses.

    httpx populates ``content-length`` on both of these responses, so the
    distinguishing header here is ``content-type``: absent, and a non-JSON
    media type. Neither is ``transfer-encoding: chunked``, so both take the
    terminal ``else`` branch of ``Client._generator``.
    """
    headers = {} if content_type is None else {"content-type": content_type}
    respx.get(f"{BASE_URL}/binary").mock(
        return_value=httpx.Response(200, headers=headers, content=b"abc")
    )
    client = make_client(stream=True)

    result = client._get_proper_res_content(client._get("binary"))

    assert result == b"abc"


@respx.mock
def test_chunked_stream_remains_an_iterator(make_client) -> None:
    """Keep chunked non-JSON successful responses iterable."""
    respx.get(f"{BASE_URL}/chunked").mock(
        return_value=httpx.Response(
            200,
            headers={"transfer-encoding": "chunked"},
            content=b"abcdef",
        )
    )
    client = make_client(stream=True)

    result = client._get_proper_res_content(client._get("chunked"))

    assert list(result) == [b"abcdef"]


@pytest.mark.parametrize(
    "content_type", ["application/json", "application/json; charset=utf-8"]
)
@respx.mock
def test_chunked_json_is_buffered_for_every_json_spelling(
    make_client, content_type: str
) -> None:
    """A chunked JSON response is buffered, whatever the media-type spelling.

    This pins a deliberate behavior change. Before media-type normalization,
    ``application/json`` won over the chunked branch and was buffered into a
    dict, while ``application/json; charset=utf-8`` fell through to the chunked
    branch and was returned as an iterator. The two spellings now agree: both
    are buffered, matching the documented contract that "if stream is specified
    but the return type is json, we will still return the json object lump sum,
    instead of a generator".
    """
    respx.get(f"{BASE_URL}/chunked-json").mock(
        return_value=httpx.Response(
            200,
            headers={
                "content-type": content_type,
                "transfer-encoding": "chunked",
            },
            json={"chunked": True},
        )
    )
    client = make_client(stream=True)

    result = client._get_proper_res_content(client._get("chunked-json"))

    assert result == {"chunked": True}


@respx.mock
def test_streamed_error_preserves_json_detail(make_client) -> None:
    """Include JSON error details after reading a streamed error response."""
    respx.get(f"{BASE_URL}/error").mock(
        return_value=httpx.Response(400, json={"error": "invalid input"})
    )
    client = make_client(stream=True)

    with pytest.raises(httpx.HTTPStatusError, match="invalid input"):
        client._get_proper_res_content(client._get("error"))
