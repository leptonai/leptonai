import json
import os

import websocket

from leptonai.api.v2.slurm import SlurmAPI
from leptonai.cli.ws_shell import (
    _receive_loop,
    encode_resize,
    encode_stdin,
    exit_code_from_status,
)


def test_stdin_and_resize_frames_use_k8s_channel_bytes():
    assert encode_stdin(b"ls -la\n") == b"\x00ls -la\n"

    frame = encode_resize(120, 40)
    assert frame[0] == 4
    assert json.loads(frame[1:].decode()) == {"Width": 120, "Height": 40}


def test_exit_code_from_status_maps_v4_status_documents():
    success = json.dumps({"metadata": {}, "status": "Success"}).encode()
    assert exit_code_from_status(success) == (0, None)

    nonzero = json.dumps({
        "status": "Failure",
        "reason": "NonZeroExitCode",
        "details": {"causes": [{"reason": "ExitCode", "message": "130"}]},
    }).encode()
    assert exit_code_from_status(nonzero) == (130, None)

    failure = json.dumps({
        "status": "Failure",
        "message": "unable to upgrade connection",
    }).encode()
    assert exit_code_from_status(failure) == (1, "unable to upgrade connection")

    assert exit_code_from_status(b"not json") == (1, "not json")


class _ScriptedSocket:
    """Replays frames like websocket-client, then closes."""

    def __init__(self, frames):
        self._frames = list(frames)

    def recv(self):
        if not self._frames:
            raise websocket.WebSocketConnectionClosedException()
        return self._frames.pop(0)


def _read_all(fd: int) -> bytes:
    os.set_blocking(fd, False)
    try:
        return os.read(fd, 65536)
    except BlockingIOError:
        return b""


def test_receive_loop_routes_channels_and_returns_exit_code():
    status = json.dumps({
        "status": "Failure",
        "reason": "NonZeroExitCode",
        "details": {"causes": [{"reason": "ExitCode", "message": "7"}]},
    })
    socket = _ScriptedSocket([
        b"\x01hello ",
        "\x01world",  # text frames must be handled like binary ones
        b"\x02oops",
        b"\x04ignored-unknown-direction",
        b"\x03" + status.encode(),
    ])
    out_read, out_write = os.pipe()
    err_read, err_write = os.pipe()
    try:
        result = _receive_loop(socket, out_write, err_write)
    finally:
        os.close(out_write)
        os.close(err_write)

    try:
        assert result == (7, None)
        assert _read_all(out_read) == b"hello world"
        assert _read_all(err_read) == b"oops"
    finally:
        os.close(out_read)
        os.close(err_read)


def test_receive_loop_treats_empty_frame_as_close():
    assert _receive_loop(_ScriptedSocket([b"\x01hi", b""]), 1, 2) == (0, None)


def test_websocket_url_swaps_scheme_only():
    assert (
        SlurmAPI._websocket_url("https://gw.example.com/api/v2/workspaces/ws")
        == "wss://gw.example.com/api/v2/workspaces/ws"
    )
    assert SlurmAPI._websocket_url("http://localhost:8080/x") == "ws://localhost:8080/x"
