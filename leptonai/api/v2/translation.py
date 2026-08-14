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

# The legacy /deployments handler injects this service port for every non-pod
# container whose port list is absent or empty.  The new endpoint controller
# does not inject a port and creates no frontend Service when the component has
# none, so the compatibility translator must reproduce the legacy default.
LEGACY_DEFAULT_ENDPOINT_PORT = 40000


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
    container: Dict[str, Any], *, for_create: bool = False
) -> Optional[List[Dict[str, Any]]]:
    # Reproduce the legacy backend's 40000 default on create. On update,
    # distinguish an omitted field (preserve live ports) from an explicit empty
    # list (clear ports), which is part of this compatibility layer's contract.
    ports = container.get("ports") if isinstance(container, dict) else None
    if ports is None:
        if not for_create:
            return None
        ports = []
    if not ports:
        return [{"container_port": LEGACY_DEFAULT_ENDPOINT_PORT}] if for_create else []

    # Several legacy exposure controls have no equivalent on
    # EndpointContainerPort.  Dropping them can turn a host-only port into an
    # ingress-exposed port, so fail explicitly instead of changing reachability.
    unsupported_fields = (
        "name",
        "expose_strategies",
        "host_port",
        "enable_load_balancer",
    )
    for index, port in enumerate(ports):
        unsupported = [
            field
            for field in unsupported_fields
            if field in port and port[field] is not None
        ]
        if unsupported:
            raise ValueError(
                "The new Endpoint API cannot represent legacy container port"
                f" field(s) {', '.join(unsupported)} on port index {index}."
            )
    # HTTPComponentSpec ports carry container_port + protocol + app_protocol
    # (api-server/httpapi/endpoint/types.go EndpointContainerPort projection).
    # app_protocol ("http"/"grpc") selects ingress routing and must survive the
    # round-trip so an image-only update does not silently clear it.
    return [
        _prune_none({
            "container_port": _get(p, "container_port", 0),
            "protocol": _get(p, "protocol"),
            "app_protocol": _get(p, "app_protocol"),
        })
        for p in ports
    ]


def _reject_unrepresentable_direct_resources(
    rr: Dict[str, Any], resource_kind: str
) -> None:
    unsupported_fields = (
        "cpu",
        "memory",
        "ephemeral_storage_in_gb",
        "accelerator_type",
        "accelerator_num",
        "resourse_affinity",
    )
    unsupported = [field for field in unsupported_fields if _get(rr, field) is not None]
    if unsupported:
        raise ValueError(
            f"The new {resource_kind} API accepts resource_shape rather than legacy"
            " direct"
            f" resource field(s): {', '.join(unsupported)}."
        )


def _legacy_spec_to_component(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Build a single HTTPComponentSpec dict from a legacy deployment spec.

    Ported from ``legacyToHTTPEndpoint`` in endpoint-api.ts: container/resource
    fields fold into the component; endpoint-level fields are lifted out (see
    :func:`legacy_to_http_endpoint`).
    """
    rr = _get(spec, "resource_requirement", {})
    _reject_unrepresentable_direct_resources(rr, "Endpoint")
    container = _get(spec, "container", {})
    component: Dict[str, Any] = {
        "name": CANONICAL_COMPONENT_NAME,
        "image": _get(container, "image"),
        "command": _get(container, "command"),
        "ports": _legacy_ports_to_component(container, for_create=True),
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
        "ingress_enabled": _get(spec, "ingress_enabled"),
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
    _reject_unrepresentable_labels(metadata, "Endpoint")
    md: Dict[str, Any] = {}
    name = _get(metadata, "name") or _get(metadata, "id")
    if name:
        md["name"] = name
    lepton_metadata = _prune_none({
        "owner": _get(metadata, "owner"),
        "visibility": _get(metadata, "visibility"),
    })
    if lepton_metadata:
        md["lepton_metadata"] = lepton_metadata
    return md


def _reject_unrepresentable_labels(
    metadata: Dict[str, Any], resource_kind: str
) -> None:
    # An empty mapping has no effect and is equivalent to omission. Only reject
    # labels whose loss would change the caller's requested metadata.
    if isinstance(metadata, dict) and metadata.get("labels"):
        raise ValueError(
            f"The new {resource_kind} API does not expose metadata labels; remove"
            " metadata.labels before creating or updating this resource."
        )


def legacy_to_http_endpoint(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy deployment create payload -> HTTPEndpoint create body.

    Ported from ``toHTTPEndpointCreatePayload`` / ``legacyToHTTPEndpoint`` in
    endpoint-api.ts. The spec collapses into a single "default" component; the
    endpoint-level fields are lifted out of the component.
    """
    spec = _get(legacy, "spec", {})
    metadata = _get(legacy, "metadata", {})
    if _get(spec, "is_pod") is True:
        raise ValueError(
            "A pod-flavoured deployment must be created through the DevPod API."
        )
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


def _require_endpoint_component_snapshot(
    raw: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return a safe live component snapshot for a destructive merge patch.

    Endpoint PATCH replaces the complete component array. A missing or malformed
    GET snapshot must therefore fail closed; fabricating a fallback component
    could delete every live component. The checks mirror the structural
    invariants guaranteed by the Endpoint backend for a valid response.
    """
    if not isinstance(raw, dict):
        raise ValueError("Endpoint preflight response must be an object.")
    raw_spec = raw.get("spec")
    if not isinstance(raw_spec, dict):
        raise ValueError("Endpoint preflight response is missing spec.components.")
    components = raw_spec.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError(
            "Endpoint preflight response spec.components must be a non-empty list."
        )

    names = set()
    frontend_count = 0
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise ValueError(
                f"Endpoint preflight component at index {index} must be an object."
            )
        name = component.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(
                f"Endpoint preflight component at index {index} is missing name."
            )
        if name in names:
            raise ValueError(
                f"Endpoint preflight response contains duplicate component {name!r}."
            )
        names.add(name)
        if component.get("frontend") is True:
            frontend_count += 1

    if len(components) > 1 and frontend_count != 1:
        raise ValueError(
            "Endpoint preflight response must contain exactly one frontend component"
            " when multiple components are present."
        )
    return components


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
    _reject_unrepresentable_direct_resources(rr, "Endpoint")
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

    components = _require_endpoint_component_snapshot(raw)
    fi = _frontend_index(components)
    next_components = [
        _merge_rfc7386(c, component_changes) if i == fi else c
        for i, c in enumerate(components)
    ]

    endpoint_spec = {"components": next_components}
    endpoint_spec.update(_legacy_endpoint_level_spec(spec))

    legacy_metadata = _get(legacy, "metadata", {})
    _reject_unrepresentable_labels(legacy_metadata, "Endpoint")
    lepton_metadata = _prune_none({
        "owner": _get(legacy_metadata, "owner"),
        "visibility": _get(legacy_metadata, "visibility"),
    })
    metadata: Dict[str, Any] = {}
    if lepton_metadata:
        metadata["lepton_metadata"] = lepton_metadata
    return {"metadata": metadata, "spec": endpoint_spec}


def build_endpoint_stop_patch(raw: Dict[str, Any]) -> Dict[str, Any]:
    """HTTPEndpoint PATCH that scales the endpoint to zero replicas.

    Ported from ``buildEndpointComponentsPatch`` in endpoint-api.ts with
    ``minReplicas: 0`` (the "terminate" case): ``min_replicas: 0`` must
    propagate to EVERY component. Resends the full component array (RFC7386
    replaces it) built from the live endpoint ``raw``.
    """
    source = _require_endpoint_component_snapshot(raw)
    next_components = []
    for c in source:
        updated = dict(c)
        updated["min_replicas"] = 0

        # Endpoint validation requires min_replicas >= 1 while either the GPU
        # or throughput target is active.  Match the dashboard's terminate path
        # by disabling those targets before scaling to zero.  Scale-down-only
        # autoscaling remains valid and is left unchanged.
        autoscaling = c.get("autoscaling")
        if isinstance(autoscaling, dict):
            throughput = autoscaling.get("target_throughput")
            qpm = throughput.get("qpm") if isinstance(throughput, dict) else None
            gpu_target = autoscaling.get("target_gpu_utilization_percentage")
            if gpu_target not in (None, 0) or qpm not in (None, 0):
                next_autoscaling = dict(autoscaling)
                next_autoscaling["target_gpu_utilization_percentage"] = 0

                next_throughput = (
                    dict(throughput) if isinstance(throughput, dict) else {}
                )
                next_throughput.update({"qpm": 0, "paths": [], "methods": []})
                next_autoscaling["target_throughput"] = next_throughput

                scale_down = autoscaling.get("scale_down")
                next_scale_down = (
                    dict(scale_down) if isinstance(scale_down, dict) else {}
                )
                next_scale_down["no_traffic_timeout"] = 0
                next_autoscaling["scale_down"] = next_scale_down
                updated["autoscaling"] = next_autoscaling
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
                    "app_protocol": _get(p, "app_protocol"),
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
        "ingress_enabled": _get(_get(ep, "spec", {}), "ingress_enabled"),
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
        "phase": phase,
        # The legacy LeptonDeploymentStatus.endpoint is a required object with an
        # external_endpoint field; always provide it so the pydantic model that
        # marks endpoint required does not reject the response.
        "endpoint": {
            "internal_endpoint": "",
            "external_endpoint": external_url or "",
        },
        "autoscaler_status": _get(status, "auto_scaler_status"),
        # Carry the endpoint's ready_replicas so the CLI list can report running
        # replicas for static endpoints (no autoscaler_status). HTTPEndpointStatus
        # omits the field when zero, so absence reads as 0.
        "ready_replicas": _get(status, "ready_replicas"),
    }
    return {
        "metadata": metadata,
        "spec": spec,
        "status": _prune_none(legacy_status),
    }


# ---------------------------------------------------------------------------
# DevPods: legacy LeptonDeployment (pod)  <->  HTTPDevPod
# ---------------------------------------------------------------------------


def _reject_unrepresentable_devpod_fields(spec: Dict[str, Any]) -> None:
    """Reject effective legacy pod settings absent from the DevPod wire.

    Health and replica spread fail validation on the legacy pod backend. The
    remaining fields affect legacy pod ingress/Envoy behavior. Silently dropping
    any of them would therefore make flag-on behavior materially different.
    """
    unsupported = []
    if "health" in spec and spec["health"] is not None:
        unsupported.append("health")

    scheduling = spec.get("scheduling_policy")
    if isinstance(scheduling, dict) and scheduling.get("replica_spread") is not None:
        unsupported.append("scheduling_policy")

    for field in ("routing_policy", "auth_config", "load_balance_config"):
        if spec.get(field):
            unsupported.append(field)

    if unsupported:
        raise ValueError(
            "The new DevPod API cannot represent legacy pod field(s): "
            + ", ".join(unsupported)
            + ". Remove them before creating this DevPod."
        )


def legacy_to_http_devpod(legacy: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy pod create payload -> HTTPDevPod create body.

    Ported from ``toHTTPDevPodCreatePayload`` in devpod-api.ts. The legacy pod
    spec's ``resource_requirement.resource_shape`` becomes a spec-level
    ``resource_shape`` string; ``is_pod`` / ``min_replicas`` / ``auto_scaler`` /
    ``api_tokens`` have no place in the devpod spec and are dropped. Rejects
    non-TCP/UDP ports, matching the new DevPod API.
    """
    spec = _get(legacy, "spec", {})
    _reject_unrepresentable_devpod_fields(spec)
    rr = _get(spec, "resource_requirement", {})
    _reject_unrepresentable_direct_resources(rr, "DevPod")
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
    legacy_metadata = _get(legacy, "metadata", {})
    _reject_unrepresentable_labels(legacy_metadata, "DevPod")
    metadata: Dict[str, Any] = {}
    name = _get(legacy_metadata, "name") or _get(legacy_metadata, "id")
    if name:
        metadata["name"] = name
    # HTTPDevPodMetadata inlines LeptonMetadata, so visibility sits directly on
    # metadata (unlike the endpoint's nested lepton_metadata). Carry it through
    # or a create with visibility=private is silently made public server-side.
    if _get(legacy_metadata, "visibility"):
        metadata["visibility"] = _get(legacy_metadata, "visibility")
    if _get(legacy_metadata, "owner"):
        metadata["owner"] = _get(legacy_metadata, "owner")
    return {"metadata": metadata, "spec": devpod_spec}


def _running_replica_count(stopped: Optional[bool]) -> int:
    return 0 if stopped is True else 1


# The devpod DevPodState enum spells NotReady without a space, but the CLI's
# LeptonDeploymentState enum expects "Not Ready"; without this remap the state
# collapses to "UNK". Every other DevPodState value matches the CLI enum, so
# unknown states pass through for the enum's own _missing_ handling.
_DEVPOD_STATE_TO_LEGACY = {"NotReady": "Not Ready"}


def _map_devpod_state_to_legacy(state: Optional[str]) -> str:
    if not state:
        return ""
    return _DEVPOD_STATE_TO_LEGACY.get(state, state)


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
    state = _map_devpod_state_to_legacy(_get(status, "state", ""))
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
        # Port status omits protocol/name and the controller emits entries only
        # for HostPortMapping ports. Pair those eligible spec ports by number
        # and occurrence; including an IngressProxy port with the same number
        # would attach the allocated host port to the wrong protocol/name.
        ports_by_number: Dict[Any, List[Dict[str, Any]]] = {}
        for port in ports:
            strategies = _get(port, "expose_strategies", []) or []
            if "HostPortMapping" in strategies:
                ports_by_number.setdefault(_get(port, "container_port"), []).append(
                    port
                )
        container_port_status = []
        for ps in port_statuses:
            candidates = ports_by_number.get(_get(ps, "container_port"), [])
            matched = candidates.pop(0) if candidates else {}
            container_port_status.append(
                _prune_none({
                    "container_port": _get(ps, "container_port"),
                    "protocol": _get(matched, "protocol", "TCP"),
                    "host_port": _get(ps, "host_port"),
                    "external_endpoint": _get(ps, "external_url"),
                    "name": _get(matched, "name"),
                })
            )

    legacy_status = _prune_none({
        "state": state or "UNK",
        "phase": state or "UNK",
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
