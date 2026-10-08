"""Interactive bridge between the local terminal and a Kubernetes-style
channel WebSocket (subprotocol ``v4.channel.k8s.io``).

Every frame starts with one channel byte: 0 carries stdin upstream, 1 and 2
deliver stdout/stderr, 3 delivers a ``metav1.Status`` JSON document when the
remote process ends, and 4 carries terminal-resize JSON upstream. An empty
stdin frame is the idle keepalive. This is the protocol behind the workspace
``/shell`` endpoints (which proxy to Kubernetes pod exec) and matches what the
dashboard terminal speaks.
"""

import json
import os
import shutil
import signal
import sys
import threading
import time
from typing import Any, Callable, Optional, Tuple

import click

STDIN_CHANNEL = 0
STDOUT_CHANNEL = 1
STDERR_CHANNEL = 2
ERROR_CHANNEL = 3
RESIZE_CHANNEL = 4

_STDIN_READ_SIZE = 4096
# The workspace ingress closes a connection after five idle minutes; ping well
# inside that, after the same minute of silence the dashboard terminal waits.
KEEPALIVE_INTERVAL_SECONDS = 60.0


def ensure_interactive_terminal() -> None:
    """Fail fast when the local end cannot host an interactive shell."""
    try:
        import termios  # noqa: F401
        import tty  # noqa: F401
    except ImportError:
        raise click.UsageError(
            "Interactive shells are not supported on this platform yet;"
            " a POSIX terminal is required."
        )
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise click.UsageError(
            "This command opens an interactive shell and requires a terminal"
            " (TTY) on stdin and stdout."
        )


def _refusal_detail(body: Any) -> Optional[str]:
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(body) if isinstance(body, str) else None
    except ValueError:
        return None
    message = payload.get("message") if isinstance(payload, dict) else None
    return message.strip() if isinstance(message, str) and message.strip() else None


def connect_shell(open_connection: Callable[[], Any]) -> Any:
    """Open a shell socket, reporting a refused handshake as a CLI error."""
    import websocket

    try:
        return open_connection()
    except websocket.WebSocketBadStatusException as error:
        # The raw exception text embeds every response header; keep the
        # status and the API's own message only.
        message = (
            "The workspace refused the shell connection"
            f" (HTTP {getattr(error, 'status_code', 'error')})"
        )
        detail = _refusal_detail(getattr(error, "resp_body", None))
        raise click.ClickException(
            f"{message}: {detail}" if detail else f"{message}."
        ) from None
    except (websocket.WebSocketException, OSError) as error:
        raise click.ClickException(
            f"Could not open the shell connection: {error}"
        ) from None


def encode_stdin(data: bytes) -> bytes:
    return bytes((STDIN_CHANNEL,)) + data


def encode_resize(columns: int, rows: int) -> bytes:
    payload = json.dumps({"Width": columns, "Height": rows})
    return bytes((RESIZE_CHANNEL,)) + payload.encode("utf-8")


def exit_code_from_status(payload: bytes) -> Tuple[int, Optional[str]]:
    """Map the error-channel ``metav1.Status`` document to an exit code.

    Returns the remote exit code plus an optional message worth surfacing
    (for failures other than a plain non-zero remote exit).
    """
    text = payload.decode("utf-8", errors="replace")
    try:
        status = json.loads(text)
    except ValueError:
        return 1, text or None
    if not isinstance(status, dict) or status.get("status") == "Success":
        return 0, None
    if status.get("reason") == "NonZeroExitCode":
        for cause in (status.get("details") or {}).get("causes") or []:
            if cause.get("reason") == "ExitCode":
                try:
                    return int(cause.get("message", "")), None
                except ValueError:
                    break
        return 1, None
    return 1, status.get("message") or None


class _Activity:
    """When shell traffic last moved; keepalives and resizes do not count."""

    def __init__(self) -> None:
        self.at = time.monotonic()

    def touch(self) -> None:
        self.at = time.monotonic()


def _send_resize(ws: Any) -> None:
    size = shutil.get_terminal_size()
    try:
        ws.send_binary(encode_resize(size.columns, size.lines))
    except Exception:
        pass  # a dead socket surfaces in the receive loop, not here


def _forward_stdin(ws: Any, fd: int, activity: Optional[_Activity] = None) -> None:
    """Pump local keystrokes to the remote stdin channel until either side
    closes. Runs on a daemon thread; shutdown is owned by the receive loop."""
    try:
        while True:
            data = os.read(fd, _STDIN_READ_SIZE)
            if not data:
                break
            ws.send_binary(encode_stdin(data))
            if activity is not None:
                activity.touch()
    except Exception:
        pass


def _forward_resizes(ws: Any, pending: threading.Event, stop: threading.Event) -> None:
    """Send a resize whenever ``pending`` is set, sized when it is sent.

    SIGWINCH interrupts the main thread, which may already hold the socket's
    send lock while answering a ping inside ``recv()``; sending from the
    handler could deadlock on that lock, so the handler only sets ``pending``.
    """
    while True:
        pending.wait()
        if stop.is_set():
            return
        pending.clear()
        _send_resize(ws)


def _keepalive(
    ws: Any,
    activity: _Activity,
    stop: threading.Event,
    interval: float = KEEPALIVE_INTERVAL_SECONDS,
) -> None:
    """Send an empty stdin frame whenever the shell has been silent for more
    than ``interval``, so an idle session is not dropped by the ingress."""
    while not stop.wait(interval):
        if time.monotonic() - activity.at <= interval:
            continue
        try:
            ws.send_binary(encode_stdin(b""))
        except Exception:
            return  # a dead socket surfaces in the receive loop, not here


def _write_all(fd: int, data: bytes) -> None:
    """Write every byte: ``os.write`` may stop short, for example when the
    SIGWINCH from a window resize interrupts a large write."""
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view) :]


def _receive_loop(
    ws: Any, stdout_fd: int, stderr_fd: int, activity: Optional[_Activity] = None
) -> Tuple[int, Optional[str]]:
    """Deliver remote output to the given fds until the socket closes."""
    import websocket

    exit_code, message = 0, None
    while True:
        try:
            frame = ws.recv()
        except (websocket.WebSocketException, ConnectionError, OSError):
            break
        if not frame:
            break
        data = frame.encode("utf-8") if isinstance(frame, str) else bytes(frame)
        channel, payload = data[0], data[1:]
        if not payload:
            continue
        if activity is not None:
            activity.touch()
        if channel == STDOUT_CHANNEL:
            _write_all(stdout_fd, payload)
        elif channel == STDERR_CHANNEL:
            _write_all(stderr_fd, payload)
        elif channel == ERROR_CHANNEL:
            # The server closes right after this frame; keep draining so the
            # close is observed rather than racing it.
            exit_code, message = exit_code_from_status(payload)
    return exit_code, message


def run_ws_shell(ws: Any) -> int:
    """Bridge the local TTY to the remote shell; returns the remote exit code.

    Puts the terminal in raw mode so every byte (including Ctrl-C) reaches
    the remote side, forwards window resizes, keeps an idle session alive, and
    restores the terminal on the way out. Call
    :func:`ensure_interactive_terminal` first.
    """
    import termios
    import tty

    stdin_fd = sys.stdin.fileno()
    saved = termios.tcgetattr(stdin_fd)
    previous_winch = None
    activity = _Activity()
    resize_pending = threading.Event()
    stop = threading.Event()
    _send_resize(ws)
    tty.setraw(stdin_fd)
    try:
        if hasattr(signal, "SIGWINCH"):
            previous_winch = signal.signal(
                signal.SIGWINCH, lambda *_args: resize_pending.set()
            )
        threading.Thread(
            target=_forward_stdin, args=(ws, stdin_fd, activity), daemon=True
        ).start()
        threading.Thread(
            target=_forward_resizes, args=(ws, resize_pending, stop), daemon=True
        ).start()
        threading.Thread(
            target=_keepalive, args=(ws, activity, stop), daemon=True
        ).start()
        exit_code, message = _receive_loop(
            ws, sys.stdout.fileno(), sys.stderr.fileno(), activity
        )
    finally:
        # Restore SIGWINCH first so its handler cannot interrupt the wake-up.
        if previous_winch is not None:
            signal.signal(signal.SIGWINCH, previous_winch)
        stop.set()
        resize_pending.set()
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, saved)
        try:
            ws.close()
        except Exception:
            pass
    if message:
        click.echo(message, err=True)
    return exit_code


def run_shell_session(open_connection: Callable[[], Any]) -> None:
    """Open the socket, bridge the TTY, and exit with the remote exit code."""
    exit_code = run_ws_shell(connect_shell(open_connection))
    if exit_code:
        raise click.exceptions.Exit(exit_code)
