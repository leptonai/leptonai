"""Resolve Slurm Teleport SSH targets from fresh workspace records.

Compute nodes resolve through their machine's runtime hostname; login nodes,
running job allocations, and Dev Pods through the hostnames their own records
publish. Every Slurm image registers its Teleport node under that hostname.
"""

from dataclasses import dataclass
import hmac
import json
import re
from typing import Optional
from urllib.parse import quote, urlsplit

from requests import RequestException

from .api_resource import APIResourse


_DNS_NAME = re.compile(
    r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?(?:\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?)*"
)
_EMAIL_LOCAL = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+")
_UNIX_LOGIN = re.compile(r"[a-zA-Z0-9_][a-zA-Z0-9._-]*")
_SLURM_JOB_ID = re.compile(r"[1-9][0-9]*")
_JOB_PAGE_SIZE = 100
_JOB_PAGE_LIMIT = 100
_COMPUTE_NOTICE = (
    "Your Slurm account must be allowed on the selected node; access may depend"
    " on your running jobs and the node's maintenance status."
)


def _object(value):
    if not isinstance(value, dict):
        raise RuntimeError("Invalid Slurm SSH API response; expected an object.")
    return value


def _dns(value):
    return isinstance(value, str) and len(value) <= 253 and _DNS_NAME.fullmatch(value)


def _live_metadata(record):
    metadata = _object(record.get("metadata"))
    deleted = metadata.get("deleted_at", 0)
    if not isinstance(deleted, (int, float)) or deleted != 0:
        raise RuntimeError("The selected SSH resource is being deleted or is invalid.")
    return metadata


def _cluster_metadata(cluster):
    metadata = _live_metadata(cluster)
    cluster_id = metadata.get("id")
    parts = cluster_id.split("/") if isinstance(cluster_id, str) else []
    if (
        len(parts) != 2
        or not all(_dns(part) for part in parts)
        or len(parts[0]) > 63
        or "." in parts[0]
        or metadata.get("name") != parts[1]
    ):
        raise RuntimeError("Invalid Slurm cluster identity for Slurm SSH.")
    return metadata


def _cluster_binding(metadata):
    return {key: metadata.get(key) for key in ("id", "uuid", "created_at", "owner")}


def _teleport_proxy(value, owner="Slurm cluster"):
    """Validate a published ``host[:443]`` Teleport proxy; return its host."""
    try:
        if (
            not isinstance(value, str)
            or any(c.isspace() for c in value)
            or "\0" in value
        ):
            raise ValueError
        proxy = urlsplit(f"https://{value}")
        if (
            not _dns(proxy.hostname)
            or proxy.port not in (None, 443)
            or proxy.username is not None
            or proxy.password is not None
            or proxy.path
            or proxy.query
            or proxy.fragment
        ):
            raise ValueError
    except ValueError:
        raise RuntimeError(
            f"The {owner} did not publish a valid Teleport proxy."
        ) from None
    return proxy.hostname


def _slurm_login(spec, actor):
    """Map the token owner's email to the cluster's Slurm Linux account."""
    ldap = _object(spec.get("ldapConfig", {}))
    suffixes = _object(ldap.get("domainSuffix", {}))
    if any(
        not _dns(domain) or not isinstance(suffix, str)
        for domain, suffix in suffixes.items()
    ):
        raise RuntimeError("Invalid Slurm LDAP username mapping.")
    local, domain = actor.split("@")
    username = local + suffixes.get(domain, "")
    if not _UNIX_LOGIN.fullmatch(username):
        raise RuntimeError("Invalid Slurm Linux username for the personal token owner.")
    return username


def _require_accessible_node(node):
    """The dashboard's node entry rule: lifecycle fields, when present, must be
    well-formed, and the node must not be inaccessible or leaving the group."""
    status = node.get("status", {})
    states = status.get("status", []) if isinstance(status, dict) else None
    if (
        not isinstance(status, dict)
        or not isinstance(status.get("inaccessible", False), bool)
        or not isinstance(status.get("machine_status", ""), str)
        or not isinstance(states, list)
        or not all(isinstance(state, str) for state in states)
    ):
        raise RuntimeError(
            "The node's lifecycle status could not be verified. Refresh the node"
            " information before connecting."
        )
    if (
        node.get("terminated")
        or node.get("deleted")
        or status.get("inaccessible")
        or {status.get("machine_status"), *states}
        & {"Terminated", "RemoveFromNodeGroup"}
    ):
        raise RuntimeError(
            "A current accessible node with a machine assignment is required for"
            " Teleport."
        )


@dataclass(frozen=True)
class NodeSSHTarget:
    actor_email: str
    cluster_name: str
    proxy: str
    username: str
    hostname: str
    # Detect replacement/reassignment while browser SSO owns the terminal.
    binding: str
    # An access condition the workspace API cannot verify for the user.
    notice: Optional[str] = None


class NodeSSHAPI(APIResourse):
    def _read(self, path, params=None):
        try:
            response = self._get(path, params=params) if params else self._get(path)
        except RequestException:
            raise RuntimeError(
                "Could not read Slurm SSH connection data from the workspace API."
            ) from None
        if response.status_code >= 400:
            # Token inventory and cluster responses can contain credentials.
            raise RuntimeError(
                f"Slurm SSH API request failed (HTTP {response.status_code})."
            )
        try:
            return response.json()
        except ValueError:
            raise RuntimeError("Invalid JSON in the Slurm SSH API response.") from None

    def _actor(self):
        workspace = _object(self._read(""))
        if workspace.get("name") != self._client.workspace_id:
            raise RuntimeError(
                "The workspace SSH identity response did not match this workspace."
            )
        if workspace.get("role") not in ("admin", "user"):
            raise RuntimeError(
                "Slurm SSH requires a personal token with workspace user or admin"
                " access."
            )
        token = self._client.auth_token or ""
        match = re.fullmatch(
            r"(nvapi-stg-|nvapi-|lapi-)([A-Za-z0-9._~+/=-]{32,})", token
        )
        if match is None:
            raise RuntimeError("Slurm SSH requires a current personal API token.")
        prefix, payload = match.groups()
        masked = f"{prefix}{payload[:6]}...{payload[-6:]}"
        tokens = self._read("/tokens")
        if not isinstance(tokens, list):
            raise RuntimeError("Invalid personal token inventory for Slurm SSH.")
        owners = [
            item.get("created_by")
            for item in tokens
            if isinstance(item, dict)
            and isinstance(item.get("masked_value"), str)
            and hmac.compare_digest(item["masked_value"].encode(), masked.encode())
        ]
        email = owners[0] if len(owners) == 1 else None
        if not isinstance(email, str) or len(email) > 254 or email.count("@") != 1:
            raise RuntimeError(
                "The current API token could not be verified as a personal user token."
            )
        local, domain = email.split("@")
        if len(local) > 64 or not _EMAIL_LOCAL.fullmatch(local) or not _dns(domain):
            raise RuntimeError(
                "The personal token owner did not have a valid canonical email."
            )
        return email

    def _clusters(self):
        clusters = self._read("/slurmclusters")
        if isinstance(clusters, dict):
            clusters = clusters.get("items")
        if not isinstance(clusters, list):
            raise RuntimeError("Invalid Slurm cluster inventory for Slurm SSH.")
        return clusters

    def _cluster(self, cluster_id):
        """The one current cluster with this NAMESPACE/NAME ID; there is no GET."""
        matches = [
            cluster
            for cluster in self._clusters()
            if _object(_object(cluster).get("metadata")).get("id") == cluster_id
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Slurm cluster {cluster_id!r} was not found.")
        return matches[0], _cluster_metadata(matches[0])

    def resolve(self, node_group_id: str, node_id: str) -> NodeSSHTarget:
        """Resolve one host-networked Slurm compute container, never a public IP."""
        if not _dns(node_group_id) or not _dns(node_id):
            raise RuntimeError("Node SSH requires a valid node group ID and node ID.")
        actor = self._actor()
        group_record = _object(
            self._read(f"/dedicated-node-groups/{quote(node_group_id, safe='')}")
        )
        group_status = group_record.get("status") or {}
        if (
            _live_metadata(group_record).get("id") != node_group_id
            or not isinstance(group_status, dict)
            or group_status.get("phase") == "Deleting"
        ):
            raise RuntimeError(
                "The selected node group is unavailable or being deleted."
            )
        matches = []
        for cluster in self._clusters():
            spec = _object(_object(cluster).get("spec"))
            for field in ("cpuNodeGroupsConfig", "gpuNodeGroupsConfig"):
                if field not in spec:
                    continue
                groups = _object(spec[field]).get("groups")
                if not isinstance(groups, list):
                    raise RuntimeError("Invalid Slurm compute group inventory.")
                for group in groups:
                    if _object(group).get("id") == node_group_id:
                        matches.append((cluster, group))
        if not matches:
            raise RuntimeError(
                "This node group has no Slurm compute assignment for Teleport SSH."
            )
        if len(matches) != 1:
            raise RuntimeError(
                "This node group has multiple Slurm compute assignments; SSH target is"
                " ambiguous."
            )
        cluster, group = matches[0]
        metadata = _cluster_metadata(cluster)
        spec = _object(cluster.get("spec"))
        if group.get("enableTeleport") is not True:
            raise RuntimeError(
                "Enable Teleport on this Slurm compute node group before connecting."
            )
        if spec.get("usePodNetworking") is True:
            raise RuntimeError(
                "This cluster uses Pod Networking. Connect to a node allocated to a"
                " running Slurm job you own with `lep slurm job ssh` instead."
            )
        if spec.get("usePodNetworking", False) is not False:
            raise RuntimeError("Invalid Slurm networking configuration.")
        proxy = _teleport_proxy(_object(cluster.get("status")).get("teleportCluster"))
        username = _slurm_login(spec, actor)
        base = f"/dedicated-node-groups/{quote(node_group_id, safe='')}"
        node = _object(self._read(f"{base}/nodes/{quote(node_id, safe='')}"))
        node_meta = _live_metadata(node)
        node_spec = _object(node.get("spec"))
        machine_id = node_spec.get("machine_id")
        if (
            node_meta.get("id") != node_id
            or node_spec.get("dedicated_node_group") != node_group_id
            or not isinstance(machine_id, str)
            or not machine_id.strip()
            or machine_id != machine_id.strip()
            or any(c in machine_id for c in "\0\r\n")
        ):
            raise RuntimeError(
                "The compute node no longer matches its selected group and machine."
            )
        _require_accessible_node(node)
        machine = _object(self._read(f"{base}/machines/{quote(machine_id, safe='')}"))
        machine_meta = _live_metadata(machine)
        status = _object(machine.get("status"))
        if (
            status.get("machine_id") != machine_id
            or status.get("node_name") != node_id
            or not _dns(status.get("hostname"))
        ):
            raise RuntimeError(
                "The machine did not report an exact node and runtime hostname."
            )
        binding = {
            "cluster": _cluster_binding(metadata),
            "node": {key: node_meta.get(key) for key in ("id", "uuid", "created_at")},
            "group": node_group_id,
            "machine_id": machine_id,
            "machine": {
                key: machine_meta.get(key) for key in ("name", "uuid", "created_at")
            },
        }
        return NodeSSHTarget(
            actor_email=actor,
            cluster_name=metadata["name"],
            proxy=proxy,
            username=username,
            hostname=status["hostname"],
            binding=json.dumps(binding, sort_keys=True),
        )

    def resolve_login(
        self, cluster_id: str, node: Optional[str] = None
    ) -> NodeSSHTarget:
        """Resolve a login node of a Ready cluster whose login nodes run Teleport.

        Without ``node`` the first current login node (by name) is chosen, as
        in the dashboard's Teleport guide.
        """
        actor = self._actor()
        cluster, metadata = self._cluster(cluster_id)
        spec = _object(cluster.get("spec"))
        status = _object(cluster.get("status", {}))
        login = _object(spec.get("loginNodesConfig", {}))
        # The API omits false booleans, so an absent flag means disabled.
        if login.get("enableTeleport") is not True:
            raise RuntimeError(
                "Teleport is not enabled for this cluster's login nodes. Use"
                " `lep slurm cluster shell` to open a login-node shell instead."
            )
        if status.get("state") != "Ready":
            raise RuntimeError(
                "Teleport SSH requires a Ready Slurm cluster"
                f" (state: {status.get('state') or 'unknown'})."
            )
        additional = login.get("additionalLoginsets")
        if additional is not None and (not isinstance(additional, list) or additional):
            raise RuntimeError(
                "This cluster has multiple login-node groups; Teleport SSH cannot"
                " determine which one you may use."
            )
        groups = login.get("allowGroups")
        if groups is not None and (
            not isinstance(groups, list)
            or not groups
            or any(
                not isinstance(name, str)
                or not name
                or name != name.strip()
                or any(c in name for c in "\0\r\n")
                for name in groups
            )
        ):
            raise RuntimeError(
                "The cluster's login-node access policy does not allow a connection."
            )
        proxy = _teleport_proxy(status.get("teleportCluster"))
        username = _slurm_login(spec, actor)
        names = status.get("loginNodeNames")
        if not isinstance(names, list) or not names or not all(map(_dns, names)):
            raise RuntimeError(
                "The Slurm cluster did not publish its current login-node names."
            )
        names = sorted(set(names))
        hostname = node if node is not None else names[0]
        if hostname not in names:
            raise RuntimeError(
                f"{node!r} is not a current login node of this cluster. Choose one"
                f" of: {', '.join(names)}."
            )
        binding = {"cluster": _cluster_binding(metadata), "login_node": hostname}
        return NodeSSHTarget(
            actor_email=actor,
            cluster_name=metadata["name"],
            proxy=proxy,
            username=username,
            hostname=hostname,
            binding=json.dumps(binding, sort_keys=True),
            notice=(
                "Your Slurm account must belong to a user group allowed by this"
                " cluster's login-node policy."
                if groups is not None
                else None
            ),
        )

    def _live_job(self, cluster_id, job_id):
        """Find the job in the live scheduler list; the detail route reads
        accounting and cannot prove a current allocation."""
        namespace, name = cluster_id.split("/")
        path = f"/slurmclusters/{quote(namespace, safe='')}/{quote(name, safe='')}/jobs"
        found = None
        for page in range(1, _JOB_PAGE_LIMIT + 1):
            response = _object(
                self._read(
                    path,
                    params={
                        "job_query_mode": "alive_only",
                        "status": "running",
                        "without_detail": "true",
                        "q": job_id,
                        "page": page,
                        "page_size": _JOB_PAGE_SIZE,
                    },
                )
            )
            jobs, total = response.get("jobs"), response.get("total")
            if (
                not isinstance(jobs, list)
                or len(jobs) > _JOB_PAGE_SIZE
                or not isinstance(total, int)
                or isinstance(total, bool)
                or total < 0
            ):
                raise RuntimeError("Invalid running Slurm job list for Slurm SSH.")
            # q also matches names; only the exact scheduler ID identifies it.
            for job in jobs:
                job_meta = _object(_object(job).get("metadata"))
                job_spec = _object(job.get("spec", {}))
                if (
                    job_meta.get("id") != job_id
                    and str(job_spec.get("job_id")) != job_id
                ):
                    continue
                if found is not None:
                    raise RuntimeError("The running Slurm job identity is ambiguous.")
                found = job
            if page * _JOB_PAGE_SIZE >= total:
                return found
            if not jobs:
                break
        raise RuntimeError("The running Slurm job list could not be fully checked.")

    def resolve_job(
        self, cluster_id: str, job_id: str, node: Optional[str] = None
    ) -> NodeSSHTarget:
        """Resolve a node allocated to a running Slurm job owned by the user."""
        if not isinstance(job_id, str) or not _SLURM_JOB_ID.fullmatch(job_id):
            raise RuntimeError("Slurm job SSH requires a numeric scheduler job ID.")
        actor = self._actor()
        cluster, metadata = self._cluster(cluster_id)
        spec = _object(cluster.get("spec"))
        groups = []
        for field in ("cpuNodeGroupsConfig", "gpuNodeGroupsConfig"):
            if field not in spec:
                continue
            entries = _object(spec[field]).get("groups")
            if not isinstance(entries, list):
                raise RuntimeError("Invalid Slurm compute group inventory.")
            groups.extend(_object(group) for group in entries)
        if not any(group.get("enableTeleport") is True for group in groups):
            raise RuntimeError(
                "Teleport is not enabled for this cluster's Slurm compute node groups."
            )
        proxy = _teleport_proxy(
            _object(cluster.get("status", {})).get("teleportCluster")
        )
        username = _slurm_login(spec, actor)
        job = self._live_job(metadata["id"], job_id)
        if job is None:
            raise RuntimeError(f"Slurm job {job_id} has no current running allocation.")
        job_meta = _live_metadata(job)
        job_spec = _object(job.get("spec", {}))
        status = _object(job.get("status", {}))
        created = job_meta.get("created_at")
        if (
            job_meta.get("id") != job_id
            or str(job_spec.get("job_id")) != job_id
            or not isinstance(created, int)
            or isinstance(created, bool)
            or created <= 0
        ):
            raise RuntimeError("The running Slurm job did not match its scheduler ID.")
        if job_meta.get("owner") != username:
            raise RuntimeError(
                "Teleport SSH requires a running Slurm job owned by your Slurm"
                f" account ({username})."
            )
        if (
            status.get("state") != "Running"
            or status.get("job_state") != "RUNNING"
            or status.get("completion_time") not in (None, 0)
        ):
            raise RuntimeError(
                "Teleport SSH requires a current running Slurm allocation."
            )
        nodes = status.get("nodes")
        if not isinstance(nodes, list) or not nodes or not all(map(_dns, nodes)):
            raise RuntimeError(
                "The running Slurm job did not report its allocated node hostnames."
            )
        nodes = sorted(set(nodes))
        if node is not None and node not in nodes:
            raise RuntimeError(
                f"{node!r} is not allocated to Slurm job {job_id}. Choose one of:"
                f" {', '.join(nodes)}."
            )
        if node is None and len(nodes) != 1:
            raise RuntimeError(
                f"Slurm job {job_id} runs on {len(nodes)} nodes. Select one with"
                f" --node: {', '.join(nodes)}."
            )
        hostname = node or nodes[0]
        binding = {
            "cluster": _cluster_binding(metadata),
            "job": {
                "id": job_id,
                "created_at": created,
                "start_time": status.get("start_time"),
                "restart_count": status.get("restart_count"),
            },
            "node": hostname,
        }
        return NodeSSHTarget(
            actor_email=actor,
            cluster_name=metadata["name"],
            proxy=proxy,
            username=username,
            hostname=hostname,
            binding=json.dumps(binding, sort_keys=True),
            notice=_COMPUTE_NOTICE,
        )

    def resolve_devpod(self, devpod_id: str) -> NodeSSHTarget:
        """Resolve the user's own Ready Slurm Dev Pod from its reported status."""
        parts = devpod_id.split("/") if isinstance(devpod_id, str) else []
        if len(parts) != 2 or not all(_dns(part) for part in parts):
            raise RuntimeError(
                "Slurm Dev Pod SSH requires a NAMESPACE/NAME Dev Pod ID."
            )
        actor = self._actor()
        namespace, name = parts
        pod = _object(
            self._read(
                f"/slurm/devpods/{quote(namespace, safe='')}/{quote(name, safe='')}"
            )
        )
        metadata = _live_metadata(pod)
        if metadata.get("id") != devpod_id or metadata.get("name") != name:
            raise RuntimeError("The Slurm Dev Pod response did not match its ID.")
        owner = metadata.get("owner")
        if not isinstance(owner, str) or owner.lower() != actor:
            raise RuntimeError("Teleport SSH requires a Slurm Dev Pod you own.")
        spec = _object(pod.get("spec"))
        status = _object(pod.get("status", {}))
        if status.get("state") != "Ready":
            raise RuntimeError(
                f"Slurm Dev Pod {devpod_id} is not Ready"
                f" (state: {status.get('state') or 'unknown'})."
            )
        if not status.get("teleportNodeName"):
            raise RuntimeError(
                "This Slurm Dev Pod does not report a Teleport node; its cluster may"
                " not enable Teleport for Dev Pods."
            )
        pod_name = status.get("podName")
        username = status.get("username")
        cluster_name = spec.get("slurmClusterName")
        if (
            not _dns(pod_name)
            or status.get("teleportNodeName") != pod_name
            or not _dns(cluster_name)
            or not isinstance(username, str)
            or not _UNIX_LOGIN.fullmatch(username)
        ):
            raise RuntimeError(
                "The Slurm Dev Pod did not report a complete Teleport target and"
                " username."
            )
        proxy = _teleport_proxy(status.get("teleportCluster"), "Slurm Dev Pod")
        binding = {
            "devpod": {
                key: metadata.get(key) for key in ("id", "uuid", "created_at", "owner")
            },
            "pod": pod_name,
        }
        return NodeSSHTarget(
            actor_email=actor,
            cluster_name=cluster_name,
            proxy=proxy,
            username=username,
            hostname=pod_name,
            binding=json.dumps(binding, sort_keys=True),
        )
