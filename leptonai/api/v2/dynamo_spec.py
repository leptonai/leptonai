"""
Pure helpers that turn CLI-style inputs into a Dynamo graph deployment spec.

Everything here is side-effect free (no API calls) so it can be unit tested
without click. The defaults registry is ported from the dashboard
(``lep-fe/interaction-specs/apps/dashboard/src/generated/forms/dynamo/helpers.ts``)
so `lep dynamo create` fills in exactly what the web console would:

- container image ``nvcr.io/nvidia/ai-dynamo/<framework>-runtime:<version>``
- working directory per framework (frontend always ``/workspace``)
- default run command per (version, serving mode, service, framework)
- the ``lepton.ai/dynamo-worker-role`` label on prefill/decode workers
- worker node groups inherited from the frontend service
- commands sent as ``["/bin/sh", "-c", "<command>"]``
"""

import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .spec_utils import make_env_vars_from_strings, make_mounts_from_strings
from .types.affinity import LeptonResourceAffinity
from .types.dynamo import (
    DYNAMO_FRONTEND_SERVICE,
    DYNAMO_SERVICE_NAMES,
    DYNAMO_WORKER_ROLE_BY_SERVICE,
    DYNAMO_WORKER_ROLE_LABEL_KEY,
    DynamoExtraPodMetadata,
    DynamoExtraPodSpec,
    DynamoMainContainerSpec,
    DynamoMultinodeSpec,
    LeptonDynamoGraphDeploymentUserSpec,
    LeptonDynamoServiceSpec,
)

# ---------------------------------------------------------------------------
# Defaults registry
# ---------------------------------------------------------------------------

DYNAMO_VERSION = "1.3.1"
SUPPORTED_DYNAMO_VERSIONS = (DYNAMO_VERSION,)

DYNAMO_FRAMEWORKS = ("vllm", "sglang", "trtllm")
DYNAMO_SERVING_MODES = ("aggregated", "disaggregated")
DYNAMO_SERVICES_BY_MODE = {
    "aggregated": ("frontend", "worker"),
    "disaggregated": ("frontend", "prefill-worker", "decode-worker"),
}
DYNAMO_WORKER_SERVICES = tuple(
    name for name in DYNAMO_SERVICE_NAMES if name != DYNAMO_FRONTEND_SERVICE
)

DYNAMO_SHELL_INTERPRETER = "/bin/sh"
DYNAMO_FRONTEND_WORKDIR = "/workspace"
DYNAMO_NAME_MAX_LENGTH = 36
DYNAMO_INGRESS_TIMEOUT_MIN = 300
DYNAMO_INGRESS_TIMEOUT_MAX = 3600

DYNAMO_RUNTIME_IMAGES = {
    "vllm": "nvcr.io/nvidia/ai-dynamo/vllm-runtime",
    "sglang": "nvcr.io/nvidia/ai-dynamo/sglang-runtime",
    "trtllm": "nvcr.io/nvidia/ai-dynamo/tensorrtllm-runtime",
}

# Ported verbatim from the dashboard's SERVICE_COMMAND registry.
# https://github.com/ai-dynamo/dynamo/tree/v1.3.1/examples/backends
_DYNAMO_SERVICE_COMMANDS = {
    "1.3.1": {
        "workdir": {
            "vllm": "/workspace/examples/backends/vllm",
            "sglang": "/workspace/examples/backends/sglang",
            "trtllm": "/workspace/",
        },
        "aggregated": {
            "frontend": {
                "vllm": "python3 -m dynamo.frontend",
                "sglang": "python3 -m dynamo.frontend",
                "trtllm": "python3 -m dynamo.frontend",
            },
            "worker": {
                "vllm": "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B",
                "sglang": (
                    "python3 -m dynamo.sglang --model-path Qwen/Qwen3-0.6B"
                    " --served-model-name Qwen/Qwen3-0.6B --page-size 16 --tp 1"
                    " --trust-remote-code --skip-tokenizer-init"
                ),
                "trtllm": (
                    "python3 -m dynamo.trtllm --model-path Qwen/Qwen3-0.6B"
                    " --served-model-name Qwen/Qwen3-0.6B --extra-engine-args"
                    " ./examples/backends/trtllm/engine_configs/qwen3/agg.yaml"
                ),
            },
        },
        "disaggregated": {
            "frontend": {
                "vllm": "python3 -m dynamo.frontend",
                "sglang": "python3 -m dynamo.frontend",
                "trtllm": "python3 -m dynamo.frontend",
            },
            "prefill-worker": {
                "vllm": (
                    "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B"
                    " --disaggregation-mode prefill --kv-transfer-config"
                    ' \'{"kv_connector":"NixlConnector","kv_role":"kv_both"}\''
                ),
                "sglang": (
                    "python3 -m dynamo.sglang --model-path Qwen/Qwen3-0.6B"
                    " --served-model-name Qwen/Qwen3-0.6B --page-size 16 --tp 1"
                    " --trust-remote-code --skip-tokenizer-init"
                    " --disaggregation-mode prefill"
                    " --disaggregation-transfer-backend nixl"
                    " --disaggregation-bootstrap-port 12345 --host 0.0.0.0"
                ),
                "trtllm": (
                    "python3 -m dynamo.trtllm --model-path Qwen/Qwen3-0.6B"
                    " --served-model-name Qwen/Qwen3-0.6B --extra-engine-args"
                    " ./examples/backends/trtllm/engine_configs/qwen3/prefill.yaml"
                    " --disaggregation-mode prefill"
                ),
            },
            "decode-worker": {
                "vllm": (
                    "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B"
                    " --disaggregation-mode decode --kv-transfer-config"
                    ' \'{"kv_connector":"NixlConnector","kv_role":"kv_both"}\''
                ),
                "sglang": (
                    "python3 -m dynamo.sglang --model-path Qwen/Qwen3-0.6B"
                    " --served-model-name Qwen/Qwen3-0.6B --page-size 16 --tp 1"
                    " --trust-remote-code --skip-tokenizer-init"
                    " --disaggregation-mode decode"
                    " --disaggregation-transfer-backend nixl"
                    " --disaggregation-bootstrap-port 12345 --host 0.0.0.0"
                ),
                "trtllm": (
                    "python3 -m dynamo.trtllm --model-path Qwen/Qwen3-0.6B"
                    " --served-model-name Qwen/Qwen3-0.6B --extra-engine-args"
                    " ./examples/backends/trtllm/engine_configs/qwen3/decode.yaml"
                    " --disaggregation-mode decode"
                ),
            },
        },
    },
}


def _command_registry(dynamo_version: Optional[str]) -> dict:
    # Unknown versions fall back to the newest known registry, as the dashboard does.
    return _DYNAMO_SERVICE_COMMANDS.get(
        dynamo_version or DYNAMO_VERSION, _DYNAMO_SERVICE_COMMANDS[DYNAMO_VERSION]
    )


def validate_framework(framework: Optional[str]) -> str:
    if framework not in DYNAMO_FRAMEWORKS:
        raise ValueError(
            f"Unsupported backend framework {framework!r}. Expected one of:"
            f" {', '.join(DYNAMO_FRAMEWORKS)}."
        )
    return framework


def validate_serving_mode(serving_mode: Optional[str]) -> str:
    if serving_mode not in DYNAMO_SERVING_MODES:
        raise ValueError(
            f"Unsupported serving mode {serving_mode!r}. Expected one of:"
            f" {', '.join(DYNAMO_SERVING_MODES)}."
        )
    return serving_mode


def validate_framework_and_mode(framework: str, serving_mode: str) -> None:
    validate_framework(framework)
    validate_serving_mode(serving_mode)
    if framework == "vllm" and serving_mode == "disaggregated":
        raise ValueError(
            "Disaggregated mode is not supported for vLLM currently. Use"
            " `--serving-mode aggregated` or pick sglang/trtllm."
        )


def get_default_image(framework: str, dynamo_version: Optional[str] = None) -> str:
    validate_framework(framework)
    return f"{DYNAMO_RUNTIME_IMAGES[framework]}:{dynamo_version or DYNAMO_VERSION}"


def get_default_working_dir(
    framework: str, service_name: str, dynamo_version: Optional[str] = None
) -> str:
    if service_name == DYNAMO_FRONTEND_SERVICE:
        return DYNAMO_FRONTEND_WORKDIR
    validate_framework(framework)
    return _command_registry(dynamo_version)["workdir"][framework]


def get_default_command(
    framework: str,
    service_name: str,
    serving_mode: str,
    dynamo_version: Optional[str] = None,
    node_count: Optional[int] = None,
    gpu_count: Optional[int] = None,
) -> str:
    """
    Default run command for a service, mirroring the dashboard. Returns "" for
    service names outside the registry. For SGLang multinode workers the
    tensor-parallel size is rewritten to ``gpu_count * node_count``.
    """
    registry = _command_registry(dynamo_version)
    base = registry.get(serving_mode, {}).get(service_name, {}).get(framework, "")
    if (
        node_count
        and node_count > 1
        and service_name != DYNAMO_FRONTEND_SERVICE
        and framework == "sglang"
    ):
        tp = (gpu_count or 1) * node_count
        if serving_mode == "disaggregated":
            return (
                base.replace("--tp 1", f"--tp-size {tp}").replace(
                    "--disaggregation-bootstrap-port 12345",
                    "--disaggregation-bootstrap-port 30001",
                )
                + " --mem-fraction-static 0.82"
            )
        return base.replace("--tp 1", f"--tp {tp}")
    return base


def shell_command_argv(command: Optional[str]) -> Optional[List[str]]:
    """``"python3 -m x"`` -> ``["/bin/sh", "-c", "python3 -m x"]``; blank -> None."""
    if command is None or not command.strip():
        return None
    normalized = command.replace("\r\n", "\n").replace("\r", "\n")
    return [DYNAMO_SHELL_INTERPRETER, "-c", normalized]


def command_display_string(argv: Optional[Sequence[str]]) -> str:
    """Inverse of :func:`shell_command_argv` for display purposes."""
    if not argv:
        return ""
    if (
        len(argv) == 3
        and argv[1] == "-c"
        and argv[0]
        in (
            "/bin/sh",
            "/bin/bash",
            "sh",
            "bash",
        )
    ):
        return argv[2]
    return shlex.join(argv)


def component_type_for_service(service_name: str) -> str:
    return "frontend" if service_name == DYNAMO_FRONTEND_SERVICE else "worker"


def serving_mode_from_services(service_names: Sequence[str]) -> str:
    """The dashboard's rule: any prefill/decode worker means disaggregated."""
    for name in service_names:
        if "prefill-worker" in name or "decode-worker" in name:
            return "disaggregated"
    return "aggregated"


def sort_service_names(service_names: Sequence[str]) -> List[str]:
    """``frontend`` first, then alphabetical (the dashboard's tab order)."""
    return sorted(
        set(service_names),
        key=lambda name: (name != DYNAMO_FRONTEND_SERVICE, name),
    )


_NAME_PATTERN = re.compile(r"^[a-z]([-a-z0-9]*[a-z0-9])?$")


def validate_dynamo_name(name: Optional[str]) -> str:
    """Name rules from the dashboard create form (same as the server's)."""
    if not name:
        raise ValueError("Name is required")
    if len(name) > DYNAMO_NAME_MAX_LENGTH:
        raise ValueError(f"Name cannot exceed {DYNAMO_NAME_MAX_LENGTH} characters.")
    if not _NAME_PATTERN.match(name):
        raise ValueError(
            "Name must consist of lower case alphanumeric characters or '-', and"
            " must start with an alphabetical character and end with an"
            " alphanumeric character."
        )
    if name.endswith("by-lepton"):
        raise ValueError("Name cannot end with 'by-lepton'")
    return name


def validate_service_name(service_name: str) -> str:
    if service_name not in DYNAMO_SERVICE_NAMES:
        raise ValueError(
            f"Unknown Dynamo service {service_name!r}. Expected one of:"
            f" {', '.join(DYNAMO_SERVICE_NAMES)}."
        )
    return service_name


def validate_service_name_for_mode(service_name: str, serving_mode: str) -> str:
    validate_service_name(service_name)
    allowed = DYNAMO_SERVICES_BY_MODE[validate_serving_mode(serving_mode)]
    if service_name not in allowed:
        raise ValueError(
            f"Service {service_name!r} is not available in {serving_mode} mode;"
            f" {serving_mode} mode allows: {', '.join(allowed)}."
        )
    return service_name


def validate_ingress_timeout(seconds: Optional[int]) -> Optional[int]:
    if seconds is None:
        return None
    if not (DYNAMO_INGRESS_TIMEOUT_MIN <= seconds <= DYNAMO_INGRESS_TIMEOUT_MAX):
        raise ValueError(
            "ingress_timeout_seconds must be between"
            f" {DYNAMO_INGRESS_TIMEOUT_MIN} and {DYNAMO_INGRESS_TIMEOUT_MAX}, got"
            f" {seconds}."
        )
    return seconds


def parse_key_value_pairs(items: Sequence[str], kind: str) -> Dict[str, str]:
    """Parse ``KEY=VALUE`` strings; both sides are required (dashboard rule)."""
    result: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid {kind} {item!r}: expected KEY=VALUE.")
        key, value = item.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            raise ValueError(f"Please input {kind} key ({item!r}).")
        if not value:
            raise ValueError(f"Please input {kind} value ({item!r}).")
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# Spec builders
# ---------------------------------------------------------------------------


@dataclass
class DynamoServiceInput:
    """
    What the CLI collects for one ``-svc/--service`` block. ``None`` means
    "not given": the value is derived from the defaults registry for a new
    service, or left untouched when overriding a service loaded from a file.
    """

    name: str
    resource_shape: Optional[str] = None
    # Dedicated node group IDs (already resolved from names).
    node_groups: Optional[List[str]] = None
    replicas: Optional[int] = None
    node_count: Optional[int] = None
    image: Optional[str] = None
    working_dir: Optional[str] = None
    command: Optional[str] = None
    envs: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    mounts: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    shared_memory_size: Optional[int] = None
    termination_grace_period_seconds: Optional[int] = None
    # GPUs per replica of the chosen shape; only used to derive the default
    # tensor-parallel size of SGLang multinode commands.
    gpu_count: Optional[int] = None


def _set_node_groups(spec: LeptonDynamoServiceSpec, node_groups: List[str]) -> None:
    if spec.affinity is None:
        spec.affinity = LeptonResourceAffinity()
    spec.affinity.allowed_dedicated_node_groups = list(node_groups)


def build_service_spec(
    svc: DynamoServiceInput,
    *,
    framework: str,
    serving_mode: str,
    dynamo_version: Optional[str] = None,
    frontend_node_groups: Optional[Sequence[str]] = None,
    image_pull_secrets: Optional[Sequence[str]] = None,
    base: Optional[LeptonDynamoServiceSpec] = None,
    framework_changed: bool = False,
    fill_defaults: bool = True,
) -> LeptonDynamoServiceSpec:
    """
    Build one service spec from CLI input, optionally on top of ``base`` (a
    service loaded from a spec file). Raises ``ValueError`` for every rule the
    dashboard enforces client side.

    With ``fill_defaults=False`` (used by `lep dynamo update`) only explicitly
    given inputs are applied on top of ``base``; missing image, working dir,
    command, replica count and pod metadata are left untouched so the derived
    merge patch contains nothing the user did not ask for.
    """
    name = svc.name
    known = name in DYNAMO_SERVICE_NAMES
    if known or base is None:
        validate_service_name_for_mode(name, serving_mode)
    is_frontend = name == DYNAMO_FRONTEND_SERVICE

    spec = base.model_copy(deep=True) if base is not None else LeptonDynamoServiceSpec()
    is_new = base is None
    if is_new:
        fill_defaults = True

    if known and (fill_defaults or not spec.component_type):
        spec.component_type = component_type_for_service(name)
    elif not spec.component_type and fill_defaults:
        spec.component_type = "worker"

    # Resource shape ---------------------------------------------------------
    if svc.resource_shape is not None:
        spec.resource_shape = svc.resource_shape
    if not spec.resource_shape:
        raise ValueError(
            f"Service {name!r} requires --resource-shape (e.g. `-svc {name}"
            " --resource-shape gpu.a10`)."
        )

    # Node groups ------------------------------------------------------------
    if is_frontend:
        if svc.node_groups is not None:
            _set_node_groups(spec, svc.node_groups)
    else:
        if (
            svc.node_groups is not None
            and frontend_node_groups is not None
            and list(svc.node_groups) != list(frontend_node_groups)
        ):
            raise ValueError(
                "Worker node groups are automatically synchronized with the"
                f" frontend service; drop --node-group on {name!r} or make it"
                " match the frontend."
            )
        if frontend_node_groups:
            _set_node_groups(spec, list(frontend_node_groups))
        elif svc.node_groups is not None:
            _set_node_groups(spec, svc.node_groups)

    # Replicas ---------------------------------------------------------------
    if svc.replicas is not None:
        if svc.replicas < 1:
            raise ValueError(f"Replicas must be at least 1 (service {name!r}).")
        spec.min_replicas = svc.replicas
        if spec.max_replicas is not None:
            spec.max_replicas = svc.replicas
    elif spec.min_replicas is None and fill_defaults:
        spec.min_replicas = 1

    # Multinode --------------------------------------------------------------
    if svc.node_count is not None:
        if is_frontend:
            raise ValueError(
                "--node-count is only supported for worker services, not the frontend."
            )
        if framework != "sglang":
            raise ValueError(
                "Multinode (--node-count) is only supported for SGLang workers;"
                f" the backend framework is {framework}."
            )
        if svc.node_count < 2:
            raise ValueError(f"Node count must be at least 2 (service {name!r}).")
        spec.multinode = DynamoMultinodeSpec(node_count=svc.node_count)
    elif framework_changed and framework != "sglang":
        # Framework cascade from the dashboard: only SGLang supports multinode.
        spec.multinode = None
    node_count = spec.multinode.node_count if spec.multinode else None

    # Main container ---------------------------------------------------------
    touch_container = fill_defaults or any(
        value is not None for value in (svc.image, svc.working_dir, svc.command)
    )
    if touch_container:
        if spec.extra_pod_spec is None:
            spec.extra_pod_spec = DynamoExtraPodSpec()
        if spec.extra_pod_spec.main_container is None:
            spec.extra_pod_spec.main_container = DynamoMainContainerSpec()
        container = spec.extra_pod_spec.main_container

        if svc.image is not None:
            container.image = svc.image
        elif fill_defaults and (is_new or framework_changed or not container.image):
            container.image = get_default_image(framework, dynamo_version)

        if svc.working_dir is not None:
            container.working_dir = svc.working_dir
        elif fill_defaults and (
            is_new or framework_changed or not container.working_dir
        ):
            container.working_dir = get_default_working_dir(
                framework, name, dynamo_version
            )

        if svc.command is not None:
            container.command = shell_command_argv(svc.command)
        elif fill_defaults and (is_new or framework_changed or not container.command):
            default_command = get_default_command(
                framework,
                name,
                serving_mode,
                dynamo_version,
                node_count=node_count,
                gpu_count=svc.gpu_count,
            )
            container.command = shell_command_argv(default_command) or container.command

    if image_pull_secrets or svc.termination_grace_period_seconds is not None:
        if spec.extra_pod_spec is None:
            spec.extra_pod_spec = DynamoExtraPodSpec()
        if image_pull_secrets:
            spec.extra_pod_spec.image_pull_secrets = list(image_pull_secrets)
        if svc.termination_grace_period_seconds is not None:
            if svc.termination_grace_period_seconds < 0:
                raise ValueError("--termination-grace-period must be non-negative.")
            spec.extra_pod_spec.termination_grace_period_seconds = (
                svc.termination_grace_period_seconds
            )

    # Envs, mounts, resources ------------------------------------------------
    if svc.envs or svc.secrets:
        spec.envs = make_env_vars_from_strings(list(svc.envs), list(svc.secrets))
    if svc.mounts:
        spec.mounts = make_mounts_from_strings(list(svc.mounts))
    if svc.shared_memory_size is not None:
        if svc.shared_memory_size < 0:
            raise ValueError("--shared-memory-size must be non-negative.")
        spec.shared_memory_size = svc.shared_memory_size

    # Pod metadata -----------------------------------------------------------
    touch_metadata = fill_defaults or bool(svc.annotations or svc.labels)
    if touch_metadata:
        if spec.extra_pod_metadata is None:
            spec.extra_pod_metadata = DynamoExtraPodMetadata()
        if svc.annotations:
            spec.extra_pod_metadata.annotations = parse_key_value_pairs(
                svc.annotations, "annotation"
            )
        if svc.labels:
            spec.extra_pod_metadata.labels = parse_key_value_pairs(svc.labels, "label")
        if spec.extra_pod_metadata.annotations is None:
            spec.extra_pod_metadata.annotations = {}
        labels = dict(spec.extra_pod_metadata.labels or {})
        labels.pop(DYNAMO_WORKER_ROLE_LABEL_KEY, None)
        role = DYNAMO_WORKER_ROLE_BY_SERVICE.get(name)
        if role:
            labels[DYNAMO_WORKER_ROLE_LABEL_KEY] = role
        spec.extra_pod_metadata.labels = labels

    return spec


def frontend_node_groups_of(
    spec: LeptonDynamoGraphDeploymentUserSpec,
) -> Optional[List[str]]:
    frontend = (spec.services or {}).get(DYNAMO_FRONTEND_SERVICE)
    if frontend is None or frontend.affinity is None:
        return None
    return frontend.affinity.allowed_dedicated_node_groups


def build_dynamo_spec(
    *,
    services: Sequence[DynamoServiceInput],
    framework: Optional[str] = None,
    serving_mode: Optional[str] = None,
    dynamo_version: Optional[str] = None,
    ingress_enabled: Optional[bool] = None,
    ingress_timeout_seconds: Optional[int] = None,
    display_name: Optional[str] = None,
    envs: Sequence[str] = (),
    secrets: Sequence[str] = (),
    image_pull_secrets: Optional[Sequence[str]] = None,
    base: Optional[LeptonDynamoGraphDeploymentUserSpec] = None,
) -> LeptonDynamoGraphDeploymentUserSpec:
    """
    Assemble a full user spec from global options plus per-service inputs,
    optionally on top of ``base`` (a spec loaded from ``lep dynamo get -p``).
    CLI values override file values; anything not given keeps the file value
    or the dashboard default.
    """
    spec = (
        base.model_copy(deep=True)
        if base is not None
        else LeptonDynamoGraphDeploymentUserSpec()
    )

    base_framework = spec.backend_framework
    framework = framework or base_framework or "vllm"
    framework_changed = bool(
        base is not None and base_framework and framework != base_framework
    )

    base_services: Dict[str, LeptonDynamoServiceSpec] = dict(spec.services or {})
    if serving_mode is None:
        serving_mode = (
            serving_mode_from_services(list(base_services))
            if base_services
            else "aggregated"
        )
    validate_framework_and_mode(framework, serving_mode)

    if spec.dynamo_namespace:
        raise ValueError(
            "dynamo_namespace is unsupported for Dynamo 1.3.1 and must be empty;"
            " remove it from the spec."
        )

    spec.backend_framework = framework
    spec.dynamo_version = dynamo_version or spec.dynamo_version or DYNAMO_VERSION
    if display_name is not None:
        spec.display_name = display_name
    if ingress_enabled is not None:
        spec.ingress_enabled = ingress_enabled
    elif spec.ingress_enabled is None:
        # The dashboard enables ingress by default; the server does not.
        spec.ingress_enabled = True
    if ingress_timeout_seconds is not None:
        spec.ingress_timeout_seconds = validate_ingress_timeout(ingress_timeout_seconds)
    else:
        validate_ingress_timeout(spec.ingress_timeout_seconds)
    if envs or secrets:
        spec.envs = make_env_vars_from_strings(list(envs), list(secrets))

    inputs_by_name: Dict[str, DynamoServiceInput] = {}
    for svc in services:
        if svc.name in inputs_by_name:
            raise ValueError(f"Service {svc.name!r} is specified more than once.")
        inputs_by_name[svc.name] = svc

    if (
        DYNAMO_FRONTEND_SERVICE not in inputs_by_name
        and DYNAMO_FRONTEND_SERVICE not in base_services
    ):
        raise ValueError(
            "A frontend service is required. Add `-svc frontend --resource-shape"
            " <shape> --node-group <node-group>`."
        )

    for name in inputs_by_name:
        validate_service_name_for_mode(name, serving_mode)
    for name in base_services:
        if name in DYNAMO_SERVICE_NAMES:
            validate_service_name_for_mode(name, serving_mode)

    common = dict(
        framework=framework,
        serving_mode=serving_mode,
        dynamo_version=spec.dynamo_version,
        image_pull_secrets=image_pull_secrets,
        framework_changed=framework_changed,
    )

    frontend_spec = build_service_spec(
        inputs_by_name.get(DYNAMO_FRONTEND_SERVICE)
        or DynamoServiceInput(name=DYNAMO_FRONTEND_SERVICE),
        base=base_services.get(DYNAMO_FRONTEND_SERVICE),
        **common,
    )
    frontend_node_groups = (
        frontend_spec.affinity.allowed_dedicated_node_groups
        if frontend_spec.affinity
        else None
    )
    if not frontend_node_groups:
        raise ValueError(
            "The frontend service requires --node-group (a dedicated node group);"
            " workers inherit it."
        )

    ordered_names = sort_service_names([*base_services.keys(), *inputs_by_name.keys()])
    new_services: Dict[str, LeptonDynamoServiceSpec] = {}
    for name in ordered_names:
        if name == DYNAMO_FRONTEND_SERVICE:
            new_services[name] = frontend_spec
            continue
        new_services[name] = build_service_spec(
            inputs_by_name.get(name) or DynamoServiceInput(name=name),
            frontend_node_groups=frontend_node_groups,
            base=base_services.get(name),
            **common,
        )
    spec.services = new_services
    return spec
