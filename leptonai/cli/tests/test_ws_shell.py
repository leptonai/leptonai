import json
import os
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import websocket

from leptonai.api.v2.slurm import SlurmAPI
from leptonai.cli.ws_shell import (
    _Activity,
    _forward_resizes,
    _forward_stdin,
    _keepalive,
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


def test_receive_loop_finishes_partial_writes():
    real_write = os.write
    out_read, out_write = os.pipe()
    # Simulate a kernel that accepts one byte per write, as an interrupted
    # write to a TTY can.
    with patch(
        "leptonai.cli.ws_shell.os.write",
        side_effect=lambda fd, data: real_write(fd, bytes(data[:1])),
    ) as write:
        result = _receive_loop(_ScriptedSocket([b"\x01hello"]), out_write, 2)
    os.close(out_write)

    try:
        assert result == (0, None)
        assert _read_all(out_read) == b"hello"
        assert write.call_count == 5
    finally:
        os.close(out_read)


def test_keepalive_pings_only_after_a_silent_interval():
    sent = []
    activity = _Activity()
    waits = []

    class Stop:
        def wait(self, timeout):
            waits.append(timeout)
            if len(waits) == 1:
                activity.touch()  # traffic just moved: no ping
            elif len(waits) == 2:
                activity.at -= 61  # a silent minute: ping on the stdin channel
            return len(waits) > 2

    _keepalive(SimpleNamespace(send_binary=sent.append), activity, Stop(), 60)

    assert sent == [b"\x00"]
    assert waits == [60, 60, 60]


def test_keepalive_stops_once_the_socket_is_gone():
    activity = _Activity()
    activity.at -= 120
    attempts = []

    def send_binary(frame):
        attempts.append(frame)
        raise OSError("closed")

    class NeverStopped:
        def wait(self, timeout):
            return False

    _keepalive(SimpleNamespace(send_binary=send_binary), activity, NeverStopped(), 60)

    assert attempts == [b"\x00"]


def test_output_and_keystrokes_reset_the_idle_clock():
    activity = _Activity()
    activity.at = 0.0
    out_read, out_write = os.pipe()
    try:
        _receive_loop(_ScriptedSocket([b"\x01hi"]), out_write, 2, activity)
    finally:
        os.close(out_write)
        os.close(out_read)
    assert activity.at > 0

    activity.at = 0.0
    sent = []
    in_read, in_write = os.pipe()
    os.write(in_write, b"ls\n")
    os.close(in_write)
    try:
        _forward_stdin(SimpleNamespace(send_binary=sent.append), in_read, activity)
    finally:
        os.close(in_read)
    assert sent == [b"\x00ls\n"]
    assert activity.at > 0


def test_resizes_are_sent_from_a_worker_not_the_signal_handler():
    sent = []
    pending, stop = threading.Event(), threading.Event()

    def send_binary(frame):
        sent.append((threading.current_thread(), frame))

    worker = threading.Thread(
        target=_forward_resizes,
        args=(SimpleNamespace(send_binary=send_binary), pending, stop),
    )
    with patch(
        "leptonai.cli.ws_shell.shutil.get_terminal_size",
        return_value=os.terminal_size((100, 30)),
    ):
        worker.start()
        pending.set()  # what the SIGWINCH handler does
        deadline = time.monotonic() + 5
        while not sent and time.monotonic() < deadline:
            time.sleep(0.01)
        stop.set()
        pending.set()
        worker.join(5)

    assert not worker.is_alive()
    assert sent == [(worker, encode_resize(100, 30))]
