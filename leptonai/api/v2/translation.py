"""Translation between the legacy LeptonDeployment schema and the new
/endpoints (HTTPEndpoint) and /devpods (HTTPDevPod) wire schemas.

The new deployment API (LEP-5664 / LEP-5665) does NOT mirror the legacy
LeptonDeployment schema. Endpoints use a multi-component model
(``spec.components[]``) and devpods use a flattened pod model
(``spec.container`` + ``spec.resource_shape`` + ``spec.stopped``). To keep the
CLI commands and SDK callers working against a single ``LeptonDeployment`` view
model regardless of which routes are live, these functions translate:

- outbound: a ``LeptonDeployment`` create/update spec -> the new wire payload
- inbound:  a new HTTPEndpoint / HTTPDevPod response -> a ``LeptonDeployment``

The mappings are ports of the dashboard's battle-tested TypeScript translators,
which solve the identical problem in production:

- endpoints: ``interaction-specs/apps/dashboard/src/endpoint-api.ts``
  (``legacyToHTTPEndpoint``, ``normalizeHTTPEndpoint``,
  ``toHTTPEndpointPatchFromRaw``, ``buildEndpointComponentsPatch``)
- devpods: ``interaction-specs/apps/dashboard/src/devpod-api.ts``
  (``normalizeHTTPDevPod``, ``toHTTPDevPodCreatePayload``, ``podStopPatch``)

Where the TypeScript and the Go wire types disagree, the Go types win
(``api-server/httpapi/endpoint/types.go``, ``api-server/httpapi/devpod/types.go``).

All functions operate on plain dicts (already alias-serialized via
``APIResourse.safe_json``) so they compose directly with the request/response
JSON boundary, and never mutate their inputs.
"""

from typing import Any, Dict, List, Optional

# The legacy deployment spec collapses into a single endpoint component. The
# frontend flag is unnecessary for a single component; the api-server treats the
# sole component as the frontend. Matches CANONICAL_COMPONENT_NAME in the TS.
CANONICAL_COMPONENT_NAME = "default"


def _get(d: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    val = d.get(key, default)
    return default if val is None else val


def _prune_none(d: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is None. Mirrors ``exclude_none`` on the wire and
    keeps merge-patch bodies from clearing untouched fields via explicit null.
    """
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# Endpoints: legacy LeptonDeployment  <->  HTTPEndpoint
# ---------------------------------------------------------------------------


def _legacy_ports_to_component(
    container: Dict[str, Any]
) -> Optional[List[Dict[str, Any]]]:
    ports = _get(container, "ports")
    if not ports:
        return None
    # HTTPComponentSpec ports carry only container_port + protocol
    # (api-server/httpapi/endpoint/types.go EndpointContainerPort projection).
    return [
        _prune_none({
            "container_port": _get(p, "container_port", 0),
            "protocol": _get(p, "protocol"),
        })
        for p in ports
    ]


def _legacy_spec_to_component(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single HTTPComponentSpec dict from a legacy deployment spec.

    Ported from ``legacyToHTTPEndpoint`` in endpoint-api.ts: container/resource
    fields fold into the component; endpoint-level fields are lifted out (see
    :func:`legacy_to_http_endpoint`).
    """
    rr = _get(spec, "resource_requirement", {})
    container = _get(spec, "container", {})
    component: Dict[str, Any] = {
        "name": CANONICAL_COMPONENT_NAME,
        "image": _get(container, "image"),
        "command": _get(container, "command"),
        "ports": _legacy_ports_to_component(container),
        "envs": _get(spec, "envs"),
        "mounts": _get(spec, "mounts"),
        "resource_shape": _get(rr, "resource_shape"),
        "min_replicas": _get(rr, "min_replicas", 1),
        "max_replicas": _get(rr, "max_replicas"),
        "shared_memory_size": _get(rr, "shared_memory_size"),
        "autoscaling": _get(spec, "auto_scaler"),
        "affinity": _get(rr, "affinity"),
        # Legacy stores host_network under resource_requirement; the new component
        # spec carries it at the component level.
        "host_network": _get(rr, "host_network"),
        "scheduling_policy": _get(spec, "scheduling_policy"),
        "queue_config": _get(spec, "queue_config"),
        "reservation_config": _get(spec, "reservation_config"),
        "health": _get(spec, "health"),
        "user_security_context": _get(spec, "user_security_context"),
    }
    return _prune_none(component)


def _legacy_endpoint_level_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Endpoint-level (non-component) HTTPEndpointSpec fields lifted from the
    legacy spec. Ported from ``legacyToHTTPEndpoint``.

    Note the key rename: legacy ``auth_config`` -> new ``access_config`` and
    legacy ``load_balance_config`` -> new ``load_balancing``
    (api-server/httpapi/endpoint/types.go).
    """
    return _prune_none({
        "ingress_timeout_seconds": _get(spec, "ingress_timeout_seconds"),
        "access_config": _get(spec, "auth_config"),
        "api_tokens": _get(spec, "api_tokens"),
        "routing_policy": _get(spec, "routing_policy"),
        "load_balancing": _get(spec, "load_balance_config"),
        "log": _get(spec, "log"),
        "metrics": _get(spec, "metrics"),
        "image_pull_secrets": _get(spec, "image_pull_secrets"),
    })


def _legacy_metadata_to_endpoint(metadata: Dict[str, Any]) -> Dict[str, Any]:
    md: Dict[str, Any] = {}
    if _get(metadata, "name"):
        md["name"] = _get(metadata, "name")
    if _get(metadata, "visibility"):
        md["lepton_metadata"] = {"visibility": _get(metadata, "visibility")}
    return md


def legacy_to_http_endpoint(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy deployment create payload -> HTTPEndpoint create body.

    Ported from ``toHTTPEndpointCreatePayload`` / ``legacyToHTTPEndpoint`` in
    endpoint-api.ts. The spec collapses into a single "default" component; the
    endpoint-level fields are lifted out of the component.
    """
    spec = _get(legacy, "spec", {})
    metadata = _get(legacy, "metadata", {})
    endpoint_spec = {"components": [_legacy_spec_to_component(spec)]}
    endpoint_spec.update(_legacy_endpoint_level_spec(spec))
    return {
        "metadata": _legacy_metadata_to_endpoint(metadata),
        "spec": endpoint_spec,
    }


def _merge_rfc7386(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """RFC7386 (JSON Merge Patch) deep merge of ``patch`` onto ``base``.

    Ported from ``mergeRFC7386`` in endpoint-api.ts: ``None`` deletes a key,
    plain dicts merge recursively, everything else replaces. (Here ``None`` is
    used only for explicit deletes; absent keys are simply not present.)
    """
    result = dict(base)
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            current = result.get(key)
            result[key] = _merge_rfc7386(
                current if isinstance(current, dict) else {}, value
            )
        else:
            result[key] = value
    return result


def _frontend_index(components: List[Dict[str, Any]]) -> int:
    for i, c in enumerate(components):
        if c.get("frontend") is True:
            return i
    return 0


def legacy_to_http_endpoint_patch(
    raw: Dict[str, Any], legacy: Dict[str, Any]
) -> Dict[str, Any]:
    """Legacy update payload -> HTTPEndpoint PATCH (RFC7386 merge) body.

    Ported from ``toHTTPEndpointPatchFromRaw`` in endpoint-api.ts. The new API
    replaces ``spec.components`` wholesale, so the patch resends the WHOLE
    component array built from the live endpoint (``raw``): the form's fields
    are overlaid onto the frontend component in place, preserving its real name
    and every field the form does not carry; sibling components pass through
    untouched. ``raw`` is the un-normalized HTTPEndpoint fetched immediately
    before the update.
    """
    spec = _get(legacy, "spec", {})
    rr = _get(spec, "resource_requirement", {})
    container = _get(spec, "container", {})

    # Component-level fields the form carries. Fields left as None are pruned so
    # the merge preserves the live component's value (no accidental clearing).
    component_changes = _prune_none({
        "image": _get(container, "image"),
        "command": _get(container, "command"),
        "ports": _legacy_ports_to_component(container),
        "envs": _get(spec, "envs"),
        "mounts": _get(spec, "mounts"),
        "resource_shape": _get(rr, "resource_shape"),
        "min_replicas": _get(rr, "min_replicas"),
        "max_replicas": _get(rr, "max_replicas"),
        "shared_memory_size": _get(rr, "shared_memory_size"),
        "autoscaling": _get(spec, "auto_scaler"),
        "affinity": _get(rr, "affinity"),
        "host_network": _get(rr, "host_network"),
        "scheduling_policy": _get(spec, "scheduling_policy"),
        "queue_config": _get(spec, "queue_config"),
        "reservation_config": _get(spec, "reservation_config"),
        "health": _get(spec, "health"),
        "user_security_context": _get(spec, "user_security_context"),
    })

    components = _get(_get(raw, "spec", {}), "components", [])
    if components:
        fi = _frontend_index(components)
        next_components = [
            _merge_rfc7386(c, component_changes) if i == fi else c
            for i, c in enumerate(components)
        ]
    else:
        next_components = [
            _merge_rfc7386({"name": CANONICAL_COMPONENT_NAME}, component_changes)
        ]

    endpoint_spec = {"components": next_components}
    endpoint_spec.update(_legacy_endpoint_level_spec(spec))

    metadata: Dict[str, Any] = {}
    if _get(_get(legacy, "metadata", {}), "visibility"):
        metadata["lepton_metadata"] = {
            "visibility": _get(_get(legacy, "metadata", {}), "visibility")
        }
    return {"metadata": metadata, "spec": endpoint_spec}


def build_endpoint_stop_patch(raw: Dict[str, Any]) -> Dict[str, Any]:
    """HTTPEndpoint PATCH that scales the endpoint to zero replicas.

    Ported from ``buildEndpointComponentsPatch`` in endpoint-api.ts with
    ``minReplicas: 0`` (the "terminate" case): ``min_replicas: 0`` must
    propagate to EVERY component. Resends the full component array (RFC7386
    replaces it) built from the live endpoint ``raw``.
    """
    components = _get(_get(raw, "spec", {}), "components", [])
    source = components if components else [{"name": CANONICAL_COMPONENT_NAME}]
    next_components = []
    for c in source:
        updated = dict(c)
        updated["min_replicas"] = 0
        next_components.append(updated)
    return {"metadata": {}, "spec": {"components": next_components}}


def _endpoint_primary_component(ep: Dict[str, Any]) -> Dict[str, Any]:
    components = _get(_get(ep, "spec", {}), "components", [])
    for c in components:
        if c.get("frontend") is True:
            return c
    return components[0] if components else {}


# Map the new EndpointState -> the legacy LeptonDeploymentState phase strings.
# Ported from mapEndpointStateToLegacyPhase in endpoint-api.ts. Unknown states
# pass through so the CLI's LeptonDeploymentState enum can classify them.
_ENDPOINT_STATE_TO_LEGACY_PHASE = {
    "Ready": "Ready",
    "NotReady": "Not Ready",
    "Starting": "Starting",
    "Updating": "Updating",
    "Scaling": "Scaling",
    "Stopping": "Stopping",
    "Stopped": "Stopped",
    "Deleting": "Deleting",
    "Error": "Error",
}


def _map_endpoint_state_to_legacy_phase(state: Optional[str]) -> str:
    if not state:
        return ""
    return _ENDPOINT_STATE_TO_LEGACY_PHASE.get(state, state)


def http_endpoint_to_legacy(ep: Dict[str, Any]) -> Dict[str, Any]:
    """HTTPEndpoint response -> legacy LeptonDeployment dict.

    Ported from ``normalizeHTTPEndpoint`` in endpoint-api.ts. The frontend
    component's fields are unfolded back into ``spec.container`` /
    ``spec.resource_requirement`` and the endpoint-level fields are placed at
    ``spec`` top level. Deleting is signalled by ``deleted_at`` -> "Deleting".
    """
    md = _get(ep, "metadata", {})
    lm = _get(md, "lepton_metadata", {})
    component = _endpoint_primary_component(ep)
    status = _get(ep, "status", {})
    name = _get(md, "name") or _get(md, "id") or ""

    if _get(md, "deleted_at"):
        phase = "Deleting"
    else:
        phase = _map_endpoint_state_to_legacy_phase(_get(status, "state"))
    # The legacy api-server folds Stopping/Stopped down to "Not Ready" in the
    # deprecated status.state field (phase keeps the real state). Reproduce it.
    if _get(md, "deleted_at"):
        state = "Deleting"
    elif phase in ("Stopping", "Stopped"):
        state = "Not Ready"
    else:
        state = phase

    ports = _get(component, "ports")
    container = _prune_none({
        "image": _get(component, "image"),
        "command": _get(component, "command"),
        "ports": (
            [
                _prune_none({
                    "container_port": _get(p, "container_port"),
                    "protocol": _get(p, "protocol"),
                })
                for p in ports
            ]
            if ports
            else None
        ),
    })

    resource_requirement = _prune_none({
        "resource_shape": _get(component, "resource_shape"),
        "min_replicas": _get(component, "min_replicas"),
        "max_replicas": _get(component, "max_replicas"),
        "shared_memory_size": _get(component, "shared_memory_size"),
        "affinity": _get(component, "affinity"),
        # Legacy carries host_network under resource_requirement (there is no
        # spec-level field); fold the component's value back in there.
        "host_network": _get(component, "host_network"),
    })

    spec = _prune_none({
        "resource_requirement": resource_requirement or None,
        "container": container or None,
        "envs": _get(component, "envs"),
        "mounts": _get(component, "mounts"),
        "api_tokens": _get(_get(ep, "spec", {}), "api_tokens"),
        "image_pull_secrets": _get(_get(ep, "spec", {}), "image_pull_secrets"),
        "queue_config": _get(component, "queue_config"),
        "auto_scaler": _get(component, "autoscaling"),
        "auth_config": _get(_get(ep, "spec", {}), "access_config"),
        "reservation_config": _get(component, "reservation_config"),
        "load_balance_config": _get(_get(ep, "spec", {}), "load_balancing"),
        "health": _get(component, "health"),
        "log": _get(_get(ep, "spec", {}), "log"),
        "metrics": _get(_get(ep, "spec", {}), "metrics"),
        "ingress_timeout_seconds": _get(
            _get(ep, "spec", {}), "ingress_timeout_seconds"
        ),
        "scheduling_policy": _get(component, "scheduling_policy"),
        "routing_policy": _get(_get(ep, "spec", {}), "routing_policy"),
        "user_security_context": _get(component, "user_security_context"),
    })

    external_url = _get(status, "external_url")
    metadata = _prune_none({
        "id": name,
        "name": name,
        "created_at": _get(md, "created_at"),
        "created_by": _get(lm, "created_by"),
        "owner": _get(lm, "owner"),
        "last_modified_at": _get(lm, "last_modified_at"),
        "last_modified_by": _get(lm, "last_modified_by"),
        "visibility": _get(lm, "visibility"),
        "version": _get(md, "version"),
        "semantic_version": _get(md, "semantic_version"),
        "resource_version": _get(md, "resource_version"),
    })
    legacy_status = {
        "state": state,
        # The legacy LeptonDeploymentStatus.endpoint is a required object with an
        # external_endpoint field; always provide it so the pydantic model that
        # marks endpoint required does not reject the response.
        "endpoint": {
            "internal_endpoint": "",
            "external_endpoint": external_url or "",
        },
        "autoscaler_status": _get(status, "auto_scaler_status"),
    }
    return {
        "metadata": metadata,
        "spec": spec,
        "status": _prune_none(legacy_status),
    }


# ---------------------------------------------------------------------------
# DevPods: legacy LeptonDeployment (pod)  <->  HTTPDevPod
# ---------------------------------------------------------------------------


def legacy_to_http_devpod(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy pod create payload -> HTTPDevPod create body.

    Ported from ``toHTTPDevPodCreatePayload`` in devpod-api.ts. The legacy pod
    spec's ``resource_requirement.resource_shape`` becomes a spec-level
    ``resource_shape`` string; ``is_pod`` / ``min_replicas`` / ``auto_scaler`` /
    ``api_tokens`` have no place in the devpod spec and are dropped. Rejects
    non-TCP/UDP ports, matching the new DevPod API.
    """
    spec = _get(legacy, "spec", {})
    rr = _get(spec, "resource_requirement", {})
    container = _get(spec, "container", {})
    for port in _get(container, "ports", []) or []:
        proto = _get(port, "protocol")
        if proto and proto not in ("TCP", "UDP"):
            raise ValueError(
                f"The new DevPod API does not support {proto} ports. Use TCP or UDP."
            )
    devpod_spec = _prune_none({
        "container": _get(spec, "container"),
        "resource_shape": _get(rr, "resource_shape"),
        "shared_memory_size": _get(rr, "shared_memory_size"),
        "affinity": _get(rr, "affinity"),
        "envs": _get(spec, "envs"),
        "mounts": _get(spec, "mounts"),
        "storage_attachments": _get(spec, "storage_attachments"),
        "image_pull_secrets": _get(spec, "image_pull_secrets"),
        "queue_config": _get(spec, "queue_config"),
        "reservation_config": _get(spec, "reservation_config"),
        "user_security_context": _get(spec, "user_security_context"),
        # Legacy stores host_network under resource_requirement; the devpod spec
        # carries it at the top level.
        "host_network": _get(rr, "host_network"),
        "log": _get(spec, "log"),
        "metrics": _get(spec, "metrics"),
        "ingress_timeout_seconds": _get(spec, "ingress_timeout_seconds"),
    })
    metadata = {}
    if _get(_get(legacy, "metadata", {}), "name"):
        metadata["name"] = _get(_get(legacy, "metadata", {}), "name")
    return {"metadata": metadata, "spec": devpod_spec}


def _running_replica_count(stopped: Optional[bool]) -> int:
    return 0 if stopped is True else 1


def http_devpod_to_legacy(dp: Dict[str, Any]) -> Dict[str, Any]:
    """HTTPDevPod response -> legacy LeptonDeployment (pod) dict.

    Ported from ``normalizeHTTPDevPod`` in devpod-api.ts. ``spec.resource_shape``
    folds into ``resource_requirement``; ``spec.stopped`` projects to
    ``min_replicas`` (0 when stopped, else 1); ``is_pod`` is forced True.
    """
    md = _get(dp, "metadata", {})
    spec = _get(dp, "spec", {})
    status = _get(dp, "status", {})
    name = _get(md, "name") or ""
    state = _get(status, "state", "")
    container = _get(spec, "container", {})
    ports = _get(container, "ports", []) or []

    resource_requirement = _prune_none({
        "resource_shape": _get(spec, "resource_shape"),
        "min_replicas": _running_replica_count(_get(spec, "stopped")),
        "shared_memory_size": _get(spec, "shared_memory_size"),
        "affinity": _get(spec, "affinity"),
        # Legacy carries host_network under resource_requirement (there is no
        # spec-level field); fold the devpod spec's value back in there.
        "host_network": _get(spec, "host_network"),
    })

    legacy_spec = _prune_none({
        "is_pod": True,
        "container": _get(spec, "container"),
        "resource_requirement": resource_requirement or None,
        "envs": _get(spec, "envs"),
        "mounts": _get(spec, "mounts"),
        "image_pull_secrets": _get(spec, "image_pull_secrets"),
        "queue_config": _get(spec, "queue_config"),
        "reservation_config": _get(spec, "reservation_config"),
        "user_security_context": _get(spec, "user_security_context"),
        "log": _get(spec, "log"),
        "metrics": _get(spec, "metrics"),
        "ingress_timeout_seconds": _get(spec, "ingress_timeout_seconds"),
    })

    external_url = _get(status, "external_url")
    container_port_status = None
    port_statuses = _get(status, "port_statuses")
    if port_statuses:
        container_port_status = []
        for ps in port_statuses:
            matched = next(
                (
                    p
                    for p in ports
                    if _get(p, "container_port") == _get(ps, "container_port")
                ),
                {},
            )
            container_port_status.append(
                _prune_none({
                    "container_port": _get(ps, "container_port"),
                    "protocol": _get(matched, "protocol", "TCP"),
                    "host_port": _get(ps, "host_port", 0),
                    "external_endpoint": _get(ps, "external_url"),
                    "name": _get(matched, "name"),
                })
            )

    legacy_status = _prune_none({
        "state": state or "UNK",
        "endpoint": {
            "internal_endpoint": "",
            "external_endpoint": external_url or "",
        },
        "container_port_status": container_port_status,
        # The devpod status exposes the pod's bare public IP directly; carry it
        # through so the CLI need not (mis)parse it out of a port's external URL.
        "public_ip": _get(status, "public_ip"),
    })

    metadata = _prune_none({
        "id": name,
        "name": name,
        "created_at": _get(md, "created_at"),
        "version": _get(md, "version"),
        "resource_version": _get(md, "resource_version"),
        "created_by": _get(md, "created_by"),
        "owner": _get(md, "owner"),
        "last_modified_by": _get(md, "last_modified_by"),
        "last_modified_at": _get(md, "last_modified_at"),
        "visibility": _get(md, "visibility"),
    })
    return {"metadata": metadata, "spec": legacy_spec, "status": legacy_status}
