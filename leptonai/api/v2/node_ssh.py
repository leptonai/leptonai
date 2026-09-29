"""Resolve Slurm compute SSH targets from fresh workspace and machine records."""

from dataclasses import dataclass
import hmac
import json
import re
from urllib.parse import quote, urlsplit

from requests import RequestException

from .api_resource import APIResourse


_DNS_NAME = re.compile(
    r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?(?:\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?)*"
)
_EMAIL_LOCAL = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+")


def _object(value):
    if not isinstance(value, dict):
        raise RuntimeError("Invalid node SSH API response; expected an object.")
    return value


def _dns(value):
    return isinstance(value, str) and len(value) <= 253 and _DNS_NAME.fullmatch(value)


def _live_metadata(record):
    metadata = _object(record.get("metadata"))
    deleted = metadata.get("deleted_at", 0)
    if not isinstance(deleted, (int, float)) or deleted != 0:
        raise RuntimeError("The selected SSH resource is being deleted or is invalid.")
    return metadata


@dataclass(frozen=True)
class NodeSSHTarget:
    actor_email: str
    cluster_name: str
    proxy: str
    username: str
    hostname: str
    # Detect replacement/reassignment while browser SSO owns the terminal.
    binding: str


class NodeSSHAPI(APIResourse):
    def _read(self, path):
        try:
            response = self._get(path)
        except RequestException:
            raise RuntimeError(
                "Could not read node SSH connection data from the workspace API."
            ) from None
        if response.status_code >= 400:
            # Token inventory and cluster responses can contain credentials.
            raise RuntimeError(
                f"Node SSH API request failed (HTTP {response.status_code})."
            )
        try:
            return response.json()
        except ValueError:
            raise RuntimeError("Invalid JSON in the node SSH API response.") from None

    def _actor(self):
        workspace = _object(self._read(""))
        if workspace.get("name") != self._client.workspace_id:
            raise RuntimeError(
                "The workspace SSH identity response did not match this workspace."
            )
        if workspace.get("role") not in ("admin", "user"):
            raise RuntimeError(
                "Node SSH requires a personal token with workspace user or admin"
                " access."
            )
        token = self._client.auth_token or ""
        match = re.fullmatch(
            r"(nvapi-stg-|nvapi-|lapi-)([A-Za-z0-9._~+/=-]{32,})", token
        )
        if match is None:
            raise RuntimeError("Node SSH requires a current personal API token.")
        prefix, payload = match.groups()
        masked = f"{prefix}{payload[:6]}...{payload[-6:]}"
        tokens = self._read("/tokens")
        if not isinstance(tokens, list):
            raise RuntimeError("Invalid personal token inventory for node SSH.")
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

    def resolve(self, node_group_id: str, node_id: str) -> NodeSSHTarget:
        """Resolve one host-networked Slurm compute container, never a public IP."""
        if not _dns(node_group_id) or not _dns(node_id):
            raise RuntimeError("Node SSH requires a valid node group ID and node ID.")
        actor = self._actor()
        clusters = self._read("/slurmclusters")
        if isinstance(clusters, dict):
            clusters = clusters.get("items")
        if not isinstance(clusters, list):
            raise RuntimeError("Invalid Slurm cluster inventory for node SSH.")
        matches = []
        for cluster in clusters:
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
            raise RuntimeError("Invalid Slurm cluster identity for node SSH.")
        spec = _object(cluster.get("spec"))
        if group.get("enableTeleport") is not True:
            raise RuntimeError(
                "Enable Teleport on this Slurm compute node group before connecting."
            )
        if spec.get("usePodNetworking") is True:
            raise RuntimeError(
                "This cluster uses Pod Networking. Open a running Slurm Job you own "
                "in the TUI and select an allocated node for Teleport SSH."
            )
        if spec.get("usePodNetworking", False) is not False:
            raise RuntimeError("Invalid Slurm networking configuration.")
        proxy_value = _object(cluster.get("status")).get("teleportCluster")
        try:
            if (
                not isinstance(proxy_value, str)
                or any(c.isspace() for c in proxy_value)
                or "\0" in proxy_value
            ):
                raise ValueError
            proxy = urlsplit(f"https://{proxy_value}")
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
                "The Slurm cluster did not publish a valid Teleport proxy."
            ) from None
        ldap = _object(spec.get("ldapConfig", {}))
        suffixes = _object(ldap.get("domainSuffix", {}))
        if any(
            not _dns(domain) or not isinstance(suffix, str)
            for domain, suffix in suffixes.items()
        ):
            raise RuntimeError("Invalid Slurm LDAP username mapping.")
        local, domain = actor.split("@")
        username = local + suffixes.get(domain, "")
        if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9._-]*", username):
            raise RuntimeError(
                "Invalid Slurm Linux username for the personal token owner."
            )
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
            "cluster": {
                key: metadata.get(key) for key in ("id", "uuid", "created_at", "owner")
            },
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
            proxy=proxy.hostname,
            username=username,
            hostname=status["hostname"],
            binding=json.dumps(binding, sort_keys=True),
        )
