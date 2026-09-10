"""Launch workload SSH sessions using the user's local Teleport client."""

from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
from typing import Callable, Optional
from urllib.parse import urlsplit

import click
from pydantic import ValidationError

from leptonai.api.v2.types.teleport import TeleportConnection, TeleportTarget


_TSH_INSTALL_URL = (
    "https://goteleport.com/docs/connect-your-client/teleport-clients/tsh/"
)
_MIN_TSH_MAJOR = 18


def _check_tsh_version(tsh: str) -> None:
    """Check the executing client version, not the proxy or re-exec source."""
    try:
        result = subprocess.run(
            [tsh, "version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise click.ClickException(
            "Timed out checking the Teleport client version. Run tsh version to "
            "check your installation."
        ) from None
    if result.returncode:
        raise click.ClickException(
            "Could not check the Teleport client version (tsh version exited with "
            f"status {result.returncode}). Run tsh version to check your installation."
        )
    match = re.search(
        r"^Teleport(?: Enterprise)? v(\d+)\.(\d+)\.(\d+)"
        r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?(?=\s|$)",
        result.stdout,
        re.MULTILINE,
    )
    if match is None:
        raise click.ClickException(
            "Could not determine the Teleport client version. "
            f"SSH requires tsh v{_MIN_TSH_MAJOR} or newer. "
            f"Run tsh version or reinstall from {_TSH_INSTALL_URL}"
        )
    if int(match.group(1)) < _MIN_TSH_MAJOR:
        version = ".".join(match.group(1, 2, 3))
        raise click.ClickException(
            f"SSH requires tsh v{_MIN_TSH_MAJOR} or newer; found v{version}. "
            f"Upgrade your Teleport CLI from {_TSH_INSTALL_URL}"
        )


def _require_tsh() -> str:
    tsh = shutil.which("tsh")
    if tsh is None:
        raise click.ClickException(
            "Teleport CLI (tsh) was not found in PATH. "
            f"Install tsh v{_MIN_TSH_MAJOR} or newer from {_TSH_INSTALL_URL}"
        )
    try:
        _check_tsh_version(tsh)
    except OSError as error:
        raise click.ClickException(
            f"Could not run Teleport CLI (tsh): {error}"
        ) from None
    except KeyboardInterrupt:
        raise click.exceptions.Exit(130) from None
    return tsh


def _status(tsh: str, proxy: Optional[str] = None) -> Optional[dict]:
    """Read the selected tsh profile, including expired profiles for discovery."""
    args = [tsh, "status"]
    if proxy is not None:
        args.append(f"--proxy={proxy}")
    args.append("--format=json")
    try:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        raise click.ClickException(
            "Timed out checking the local Teleport login."
        ) from None
    if result.returncode != 0:
        if "not logged in" in result.stderr.lower():
            return None
        # Expired profiles can still include JSON; parse those below. Other
        # tool failures must not trigger a misleading SSO login loop.
        if not result.stdout.strip():
            raise click.ClickException(
                "Could not check the local Teleport login (tsh status exited with "
                f"status {result.returncode}). Run tsh status --format=json to "
                "see the error and check your tsh installation."
            )
    try:
        status = json.loads(result.stdout)
        active = status.get("active") if isinstance(status, dict) else None
        if active is None:
            return None
        if not isinstance(active, dict):
            raise ValueError
        return active
    except (ValueError, TypeError):
        raise click.ClickException(
            "Could not read the local Teleport profile."
        ) from None


def _profile(tsh: str, connection: TeleportTarget) -> Optional[dict]:
    """Return a current profile for the exact proxy and cluster, if present."""
    active = _status(tsh, f"{connection.proxy}:{connection.port}")
    if active is None:
        return None
    try:
        proxy = urlsplit(active["profile_url"])
        if (
            proxy.scheme != "https"
            or proxy.hostname != connection.proxy.lower()
            or (proxy.port or 443) != connection.port
            or proxy.username is not None
            or proxy.password is not None
            or proxy.path not in ("", "/")
            or proxy.query
            or proxy.fragment
            or active.get("cluster") != connection.cluster_domain
        ):
            return None
        expiry = datetime.fromisoformat(active["valid_until"].replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            raise ValueError
        if expiry <= datetime.now(timezone.utc):
            return None
        if (
            not isinstance(active.get("username"), str)
            or not active["username"]
            or any(c in active["username"] for c in "\0\r\n")
        ):
            raise ValueError
        logins = active.get("logins")
        if not isinstance(logins, list) or not all(isinstance(v, str) for v in logins):
            raise ValueError
        return active
    except (ValueError, TypeError, KeyError, AttributeError):
        raise click.ClickException(
            "Could not read the local Teleport profile. Check your tsh installation "
            "and run tsh login for this proxy."
        ) from None


def _run_interactive(args: list, operation: str) -> None:
    # Inherit all three streams so browser/SSO prompts and the SSH terminal work.
    result = subprocess.run(args, check=False)
    if result.returncode:
        code = result.returncode if result.returncode > 0 else 128 - result.returncode
        click.echo(f"Teleport {operation} exited with status {code}.", err=True)
        raise click.exceptions.Exit(code)


def connect_teleport(
    connection: TeleportTarget,
    auth: str = "Starfleet",
    *,
    workspace: Optional[str] = None,
    before_connect: Optional[Callable[[], None]] = None,
) -> None:
    """Reuse a valid tsh profile, log in if needed, then hand over the terminal."""
    if isinstance(connection, TeleportConnection) and connection.status != "Running":
        raise click.ClickException(
            "The pod is not reporting a running Teleport connection. "
            "Check Teleport SSH Access in the dashboard and retry when it is ready."
        )
    _connect_teleport(
        _require_tsh(),
        connection,
        auth,
        workspace=workspace,
        before_connect=before_connect,
    )


def _connect_teleport(
    tsh: str,
    connection: TeleportTarget,
    auth: str,
    *,
    workspace: Optional[str] = None,
    before_connect: Optional[Callable[[], None]] = None,
) -> None:
    """Start a session after client preflight, without checking the client twice."""
    proxy = f"--proxy={connection.proxy}:{connection.port}"
    try:
        profile = _profile(tsh, connection)
        if profile is None:
            click.echo("Signing in to Teleport...")
            _run_interactive(
                [tsh, "login", proxy, f"--auth={auth}", connection.cluster_domain],
                "login",
            )
            profile = _profile(tsh, connection)
            if profile is None:
                raise click.ClickException(
                    "Teleport login did not produce a valid profile for the target's "
                    "proxy and cluster."
                )
        if connection.username not in profile["logins"]:
            raise click.ClickException(
                "Your Teleport identity is not authorized to log in as"
                f" {connection.username}. Check your Teleport access or sign in with"
                " the correct account."
            )
        if before_connect is not None:
            before_connect()
        node = connection.name
        if workspace is not None:
            node = _job_node(tsh, connection, profile["username"], workspace)
        _run_interactive(
            [
                tsh,
                "ssh",
                proxy,
                f"--cluster={connection.cluster_domain}",
                f"--user={profile['username']}",
                f"{connection.username}@{node}",
            ],
            "SSH",
        )
    except KeyboardInterrupt:
        raise click.exceptions.Exit(130) from None
    except OSError as error:
        raise click.ClickException(
            f"Could not run Teleport CLI (tsh): {error}"
        ) from None


def _job_node(tsh: str, target: TeleportTarget, user: str, workspace: str) -> str:
    """Resolve the exact registered hostname to one Teleport node ID."""
    try:
        result = subprocess.run(
            [
                tsh,
                "ls",
                f"--proxy={target.proxy}:{target.port}",
                f"--cluster={target.cluster_domain}",
                f"--user={user}",
                "--format=json",
                f"--search={target.name}",
                f"teleport.lepton.ai/workspace={workspace}",
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        raise click.ClickException(
            "Timed out discovering the Job's Teleport node."
        ) from None
    if result.returncode:
        raise click.ClickException(
            "Could not list Teleport nodes. Check your Teleport login, permissions, "
            "and --teleport-proxy."
        )
    try:
        nodes = json.loads(result.stdout)
        if not isinstance(nodes, list):
            raise ValueError
        matches = []
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError
            metadata, spec = node.get("metadata"), node.get("spec")
            if not isinstance(metadata, dict) or not isinstance(spec, dict):
                raise ValueError
            labels = metadata.get("labels")
            if (
                node.get("kind") == "node"
                and spec.get("hostname") == target.name
                and isinstance(labels, dict)
                and labels.get("teleport.lepton.ai/workspace") == workspace
            ):
                node_id = metadata.get("name")
                if not isinstance(node_id, str) or not re.fullmatch(
                    r"[a-zA-Z0-9][a-zA-Z0-9._-]*", node_id
                ):
                    raise ValueError
                matches.append(node_id)
    except (ValueError, TypeError):
        raise click.ClickException("Teleport returned an invalid node list.") from None
    if not matches:
        raise click.ClickException(
            "No Teleport node is visible for this Job replica. Verify the proxy, "
            "job_teleport enablement, and that the Job image starts a Teleport agent."
        )
    if len(matches) != 1:
        raise click.ClickException(
            "Multiple Teleport nodes match this Job replica. Wait for stale "
            "registrations to expire or ask your administrator to resolve them."
        )
    return matches[0]


def connect_job_teleport(
    workspace: str,
    replica: str,
    *,
    proxy: Optional[str] = None,
    auth: str = "Starfleet",
    before_connect: Optional[Callable[[], None]] = None,
) -> None:
    """Job APIs omit Teleport metadata; use an explicit proxy or the tsh profile."""
    tsh = _require_tsh()
    try:
        if proxy is not None:
            if any(c.isspace() for c in proxy) or "\0" in proxy:
                raise ValueError
            url = urlsplit(f"https://{proxy}")
            cluster = url.hostname
        else:
            active = _status(tsh)
            if active is None:
                raise click.ClickException(
                    "No Teleport profile is selected. Use --teleport-proxy"
                    " <host[:port]> or run tsh login first."
                )
            url = urlsplit(active["profile_url"])
            cluster = active.get("cluster")
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError
        # Explicit Lepton proxies use LEPTON_TELEPORT_CLUSTER as their cluster.
        target = TeleportTarget(
            name=f"{workspace}-{replica}",
            proxy=url.hostname,
            port=url.port if url.port is not None else 443,
            clusterDomain=cluster,
            username="root",
        )
    except (ValueError, TypeError, KeyError, ValidationError):
        raise click.ClickException(
            "Invalid Teleport proxy or Job replica. Use --teleport-proxy <host[:port]>."
        ) from None
    except OSError as error:
        raise click.ClickException(
            f"Could not run Teleport CLI (tsh): {error}"
        ) from None
    except KeyboardInterrupt:
        raise click.exceptions.Exit(130) from None
    click.echo(
        f"Connecting to Job replica {replica} via Teleport"
        f" ({target.proxy}:{target.port})..."
    )
    _connect_teleport(
        tsh, target, auth, workspace=workspace, before_connect=before_connect
    )
