import httpx
import pytest
import respx

from leptonai.client import Client


BASE_URL = "https://deployment.example"


@pytest.fixture
def make_client():
    clients = []

    def _make_client(*, stream):
        client = Client.__new__(Client)
        client.url = BASE_URL
        client.stream = stream
        client.chunk_size = 2
        client._session = httpx.Client()
        clients.append(client)
        return client

    yield _make_client

    for client in clients:
        client._session.close()


def test_decodes_buffered_binary_response(make_client):
    client = make_client(stream=False)

    with respx.mock:
        respx.get(f"{BASE_URL}/data").mock(
            return_value=httpx.Response(200, content=b"binary")
        )

        response = client._get("data")
        assert client._get_proper_res_content(response) == b"binary"


@pytest.mark.parametrize("has_content_length", [True, False])
def test_decodes_non_chunked_streaming_binary_response(make_client, has_content_length):
    client = make_client(stream=True)
    response = (
        httpx.Response(200, content=b"binary")
        if has_content_length
        else httpx.Response(200, stream=httpx.ByteStream(b"binary"))
    )
    assert ("content-length" in response.headers) is has_content_length

    with respx.mock:
        respx.get(f"{BASE_URL}/data").mock(return_value=response)

        response = client._get("data")
        assert client._get_proper_res_content(response) == b"binary"


@pytest.mark.parametrize("stream", [False, True])
def test_decodes_json_content_type_with_charset(make_client, stream):
    client = make_client(stream=stream)

    with respx.mock:
        respx.get(f"{BASE_URL}/data").mock(
            return_value=httpx.Response(
                200,
                json={"result": "ok"},
                headers={"content-type": "application/json; charset=utf-8"},
            )
        )

        response = client._get("data")
        assert client._get_proper_res_content(response) == {"result": "ok"}


def test_decodes_exact_json_content_type(make_client):
    client = make_client(stream=True)

    with respx.mock:
        respx.get(f"{BASE_URL}/data").mock(
            return_value=httpx.Response(
                200,
                json={"result": "ok"},
                headers={"content-type": "application/json"},
            )
        )

        response = client._get("data")
        assert client._get_proper_res_content(response) == {"result": "ok"}


def test_preserves_chunked_streaming_response(make_client):
    client = make_client(stream=True)

    with respx.mock:
        respx.get(f"{BASE_URL}/data").mock(
            return_value=httpx.Response(
                200,
                content=b"binary",
                headers={"transfer-encoding": "chunked"},
            )
        )

        response = client._get("data")
        content = client._get_proper_res_content(response)
        assert not isinstance(content, bytes)
        assert b"".join(content) == b"binary"


def test_preserves_streaming_http_error_details(make_client):
    client = make_client(stream=True)

    with respx.mock:
        respx.get(f"{BASE_URL}/data").mock(
            return_value=httpx.Response(400, json={"error": "invalid input"})
        )

        response = client._get("data")
        with pytest.raises(httpx.HTTPStatusError, match="Detail: invalid input"):
            client._get_proper_res_content(response)
