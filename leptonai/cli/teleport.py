"""Launch workload SSH sessions using the user's local Teleport client."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
from typing import Callable, Optional
from urllib.parse import urlsplit

import click
from pydantic import ValidationError
from requests import RequestException

from leptonai.api.v2.node_ssh import NodeSSHTarget
from leptonai.api.v2.types.teleport import TeleportConnection, TeleportTarget


_TSH_INSTALL_URL = (
    "https://goteleport.com/docs/connect-your-client/teleport-clients/tsh/"
)
_MIN_TSH_MAJOR = 18


@dataclass(frozen=True)
class _Workload:
    """Wording for a workload whose Lepton agent registers a Teleport node."""

    noun: str
    requirement: str


_JOB_REPLICA = _Workload(
    "Job replica",
    "job_teleport enablement, and that the Job image starts a Teleport agent",
)
_DEV_POD = _Workload(
    "Dev Pod",
    "dev_pod_teleport and node group enablement, and that the Dev Pod runs the"
    " default entrypoint, which starts its Teleport agent",
)


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


def _profile(
    tsh: str,
    connection: TeleportTarget,
    *,
    discover_cluster: bool = False,
    expected_user: Optional[str] = None,
) -> Optional[dict]:
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
            or (
                not discover_cluster
                and active.get("cluster") != connection.cluster_domain
            )
            or (expected_user is not None and active.get("username") != expected_user)
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
        if not isinstance(active.get("cluster"), str) or not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9._-]*", active["cluster"]
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
    workload: _Workload = _JOB_REPLICA,
    before_connect: Optional[Callable[[], None]] = None,
    slurm_cluster: Optional[str] = None,
    expected_user: Optional[str] = None,
) -> None:
    """Start a session after client preflight, without checking the client twice."""
    proxy = f"--proxy={connection.proxy}:{connection.port}"
    try:
        profile_options = dict(
            discover_cluster=slurm_cluster is not None, expected_user=expected_user
        )
        profile = _profile(tsh, connection, **profile_options)
        if profile is None:
            click.echo("Signing in to Teleport...")
            login_args = [tsh, "login", proxy, f"--auth={auth}"]
            if expected_user is not None:
                login_args.append(f"--user={expected_user}")
            if slurm_cluster is None:
                login_args.append(connection.cluster_domain)
            _run_interactive(
                login_args,
                "login",
            )
            profile = _profile(tsh, connection, **profile_options)
            if profile is None:
                raise click.ClickException(
                    "Teleport login did not produce a valid profile for the target's "
                    "proxy, cluster, and user."
                )
        if connection.username not in profile["logins"]:
            raise click.ClickException(
                "Your Teleport identity is not authorized to log in as"
                f" {connection.username}. Check your Teleport access or sign in with"
                " the correct account."
            )
        if before_connect is not None and slurm_cluster is None:
            before_connect()
        node = connection.name
        if workspace is not None:
            node = _job_node(tsh, connection, profile["username"], workspace, workload)
        if slurm_cluster is not None:
            connection = TeleportTarget(**{
                **connection.model_dump(by_alias=True),
                "clusterDomain": profile["cluster"],
            })
            node = _slurm_node(tsh, connection, profile["username"], slurm_cluster)
            if before_connect is not None:
                before_connect()
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
    except RequestException:
        # Only before_connect reads the API here. RequestException is also an
        # OSError, so it must not be reported as a tsh failure below.
        raise click.ClickException(
            "Could not recheck the SSH target with the workspace API after"
            " sign-in. Retry the command."
        ) from None
    except OSError as error:
        raise click.ClickException(
            f"Could not run Teleport CLI (tsh): {error}"
        ) from None


def _slurm_node(tsh: str, target: TeleportTarget, user: str, cluster: str) -> str:
    labels = {"teleport.lepton.ai/slurm-cluster": cluster, "cluster": cluster}
    try:
        result = subprocess.run(
            [
                tsh,
                "ls",
                f"--proxy={target.proxy}:{target.port}",
                f"--cluster={target.cluster_domain}",
                f"--user={user}",
                "--format=json",
                ",".join(f"{key}={value}" for key, value in labels.items()),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        raise click.ClickException(
            "Timed out discovering the Slurm node in Teleport."
        ) from None
    if result.returncode:
        raise click.ClickException(
            "Could not list Slurm Teleport nodes. Check your Teleport login and"
            " permissions."
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
            actual_labels = metadata.get("labels")
            if (
                node.get("kind") != "node"
                or not isinstance(actual_labels, dict)
                or any(actual_labels.get(key) != value for key, value in labels.items())
                or actual_labels.get("hostname") != target.name
            ):
                continue
            host_id = metadata.get("name")
            hostname = spec.get("hostname")
            if any(
                not isinstance(value, str)
                or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", value)
                for value in (host_id, hostname)
            ):
                raise ValueError
            matches.append(host_id)
    except (ValueError, TypeError):
        raise click.ClickException("Teleport returned an invalid node list.") from None
    if not matches:
        raise click.ClickException(
            "No Teleport node is visible for this Slurm node. Check agent"
            " registration and permissions."
        )
    if len(matches) != 1:
        raise click.ClickException(
            "Multiple Teleport nodes match this Slurm node. Resolve stale"
            " registrations before retrying."
        )
    return matches[0]


def connect_node_teleport(
    target: NodeSSHTarget,
    auth: str = "Starfleet",
    *,
    before_connect: Optional[Callable[[], None]] = None,
    description: Optional[str] = None,
) -> None:
    """Discover the Teleport cluster from the verified personal user's profile.

    Serves every Slurm target: compute containers, login nodes, job
    allocations, and Dev Pods all register under their runtime hostname.
    """
    connection = TeleportTarget(
        name=target.hostname,
        proxy=target.proxy,
        port=443,
        clusterDomain=target.proxy,
        username=target.username,
    )
    if target.notice:
        click.echo(f"Note: {target.notice}")
    description = description or f"Slurm compute container {target.hostname}"
    click.echo(f"Connecting to {description} as {target.username} via Teleport...")
    _connect_teleport(
        _require_tsh(),
        connection,
        auth,
        slurm_cluster=target.cluster_name,
        expected_user=target.actor_email,
        before_connect=before_connect,
    )


def _job_node(
    tsh: str,
    target: TeleportTarget,
    user: str,
    workspace: str,
    workload: _Workload = _JOB_REPLICA,
) -> str:
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
            f"Timed out discovering the {workload.noun}'s Teleport node."
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
            f"No Teleport node is visible for this {workload.noun}. Verify the"
            f" proxy, {workload.requirement}."
        )
    if len(matches) != 1:
        raise click.ClickException(
            f"Multiple Teleport nodes match this {workload.noun}. Wait for stale "
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
    _connect_workload_teleport(
        workspace,
        f"{workspace}-{replica}",
        _JOB_REPLICA,
        f"Job replica {replica}",
        proxy=proxy,
        auth=auth,
        before_connect=before_connect,
    )


def connect_devpod_teleport(
    workspace: str,
    hostname: str,
    name: str,
    *,
    proxy: Optional[str] = None,
    auth: str = "Starfleet",
    before_connect: Optional[Callable[[], None]] = None,
) -> None:
    """New-API Dev Pods omit Teleport metadata too; same proxy rules as Jobs."""
    _connect_workload_teleport(
        workspace,
        hostname,
        _DEV_POD,
        f"Dev Pod {name}",
        proxy=proxy,
        auth=auth,
        before_connect=before_connect,
    )


def _connect_workload_teleport(
    workspace: str,
    hostname: str,
    workload: _Workload,
    description: str,
    *,
    proxy: Optional[str],
    auth: str,
    before_connect: Optional[Callable[[], None]],
) -> None:
    tsh = _require_tsh()
    try:
        if proxy is not None:
            if any(c.isspace() for c in proxy) or "\0" in proxy:
                raise ValueError
            url = urlsplit(f"https://{proxy}")
            # An explicit proxy uses its hostname as the cluster name.
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
        target = TeleportTarget(
            name=hostname,
            proxy=url.hostname,
            port=url.port if url.port is not None else 443,
            clusterDomain=cluster,
            username="root",
        )
    except (ValueError, TypeError, KeyError, ValidationError):
        raise click.ClickException(
            f"Invalid Teleport proxy or {workload.noun}. Use --teleport-proxy"
            " <host[:port]>."
        ) from None
    except OSError as error:
        raise click.ClickException(
            f"Could not run Teleport CLI (tsh): {error}"
        ) from None
    except KeyboardInterrupt:
        raise click.exceptions.Exit(130) from None
    click.echo(
        f"Connecting to {description} via Teleport ({target.proxy}:{target.port})..."
    )
    _connect_teleport(
        tsh,
        target,
        auth,
        workspace=workspace,
        workload=workload,
        before_connect=before_connect,
    )
