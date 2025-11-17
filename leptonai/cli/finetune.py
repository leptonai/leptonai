import json
from typing import Any, Dict, List, Optional

import click
from loguru import logger
from rich.table import Table

from .util import (
    click_group,
    console,
    format_timestamp_ms,
    colorize_state,
    make_name_id_cell,
    _validate_queue_priority,
    apply_nodegroup_and_queue_config,
)
from ..api.v2.client import APIClient
from leptonai.api.v1.types.job import LeptonJobQueryMode, LeptonJobSegmentConfig
from leptonai.api.v1.types.common import Metadata, LeptonVisibility
from leptonai.api.v1.photon import make_mounts_from_strings
from leptonai.api.v2.types.finetune import (
    LeptonFineTuneJob,
    LeptonFineTuneJobSpec,
    Trainer,
)


def _fetch_template_schema(template_id: str) -> Dict[str, Any]:
    """Fetch json_schema of a template by id. Prefer public, fallback to private."""
    client = APIClient()
    try:
        tpl = client.template.get_public(template_id)
        logger.trace(json.dumps(tpl.model_dump(), indent=2))
    except Exception:
        tpl = None
    if tpl is None:
        try:
            tpl = client.template.get_private(template_id)
        except Exception:
            tpl = None
    if tpl and getattr(tpl, "spec", None):
        schema = getattr(tpl.spec, "json_schema", None) or {}
        if isinstance(schema, dict):
            return schema
        # Some backends may serialize json_schema as string
        if isinstance(schema, str):
            try:
                return json.loads(schema)
            except Exception:
                return {}
    return {}


class DynamicSchemaCommand(click.Command):
    """A Click command that injects options at runtime from a template's json_schema."""

    _generated_for_template: Optional[str] = None

    def make_context(self, info_name, args, parent=None, **extra):
        template_id = self._parse_template_arg(args) or "nemo-automodel"
        if template_id and template_id != self._generated_for_template:
            schema = _fetch_template_schema(template_id)
            self.params += self._build_options_from_schema(schema)
            self._generated_for_template = template_id
        return super().make_context(info_name, args, parent=parent, **extra)

    @staticmethod
    def _parse_template_arg(args: List[str]) -> Optional[str]:
        for i, a in enumerate(args):
            if a in ("-t", "--template", "--template-id") and i + 1 < len(args):
                return args[i + 1]
            if a.startswith("--template="):
                return a.split("=", 1)[1]
            if a.startswith("--template-id="):
                return a.split("=", 1)[1]
        return None

    @staticmethod
    def _build_options_from_schema(schema: Dict[str, Any]) -> List[click.Option]:
        props: Dict[str, Any] = (schema or {}).get("properties", {}) or {}
        required: List[str] = (schema or {}).get("required", []) or []
        options: List[click.Option] = []

        def flag(name: str) -> str:
            return f"--{name.replace('_', '-')}"

        def _parse_kv_list(ctx, param, values):
            result: Dict[str, str] = {}
            for raw in values or []:
                key, sep, val = (raw or "").partition(":")
                if not sep or key.strip() == "":
                    raise click.BadParameter(
                        "expected KEY:VALUE (use multiple flags for multiple items)",
                        param=param,
                    )
                result[key.strip()] = val.strip()
            return result

        for name, prop in props.items():
            desc = prop.get("description", "")
            default = prop.get("default", None)
            ptype = prop.get("type", "string")
            addl = prop.get("additionalProperties")
            is_string_mapping = (
                ptype == "object"
                and isinstance(addl, dict)
                and addl.get("type") == "string"
            )
            param_decls: Any
            if ptype == "boolean":
                param_decls = (f"{flag(name)}/--no-{name.replace('_','-')}",)
                options.append(
                    click.Option(
                        param_decls,
                        help=desc,
                        default=bool(default) if default is not None else False,
                        show_default=True,
                    )
                )
            elif ptype == "integer":
                options.append(
                    click.Option(
                        (flag(name),),
                        type=int,
                        default=default,
                        required=name in required,
                        help=desc,
                        show_default=True,
                    )
                )
            elif ptype == "number":
                options.append(
                    click.Option(
                        (flag(name),),
                        type=float,
                        default=default,
                        required=name in required,
                        help=desc,
                        show_default=True,
                    )
                )
            else:
                if is_string_mapping:
                    options.append(
                        click.Option(
                            (flag(name),),
                            type=str,
                            multiple=True,
                            required=name in required,
                            callback=_parse_kv_list,
                            help=((desc + " — ") if desc else "")
                            + "repeatable KEY:VALUE (e.g., question:prompt)",
                            show_default=False,
                        )
                    )
                else:
                    options.append(
                        click.Option(
                            (flag(name),),
                            type=str,
                            default=default,
                            required=name in required,
                            help=desc
                            + (" (JSON)" if ptype in ("object", "array") else ""),
                            show_default=True,
                        )
                    )
        return options


@click_group()
def finetune():
    """Manage finetuning workflows."""
    pass


def _print_finetune_jobs_table(jobs, dashboard_base_url: Optional[str] = None):
    table = Table(show_header=True, show_lines=True)
    table.add_column("Name / ID")
    table.add_column("Created At")
    table.add_column("State")
    table.add_column("User ID")
    table.add_column("Shape / Node Group")
    table.add_column("Workers")
    table.add_column("Base Model")
    table.add_column("Dataset")

    for job in jobs:
        md = getattr(job, "metadata", None) or {}
        status = getattr(job, "status", None) or {}
        spec = getattr(job, "spec", None) or {}
        # Dashboard link: utilities/fine-tune/jobs/detail/<jid>
        job_url = (
            f"{dashboard_base_url}/utilities/fine-tune/jobs/detail/{getattr(md, 'id_', '')}"
            if dashboard_base_url and getattr(md, "id_", None)
            else None
        )
        name_id_cell = make_name_id_cell(
            getattr(md, "name", None),
            getattr(md, "id_", None),
            link=job_url,
            link_target="id",
        )
        created_ts = format_timestamp_ms(getattr(md, "created_at", None))
        state_cell = colorize_state(getattr(status, "state", None))
        owner = getattr(md, "owner", "-")
        # Node groups
        try:
            ngs = getattr(
                getattr(spec, "affinity", None), "allowed_dedicated_node_groups", None
            )
            ng_str = "\n".join(ngs).lower() if ngs else ""
        except Exception:
            ng_str = ""
        # Workers and shape from spec
        workers = (
            getattr(spec, "completions", None)
            or getattr(spec, "parallelism", None)
            or 1
        )
        shape = getattr(spec, "resource_shape", None) or "-"
        # Colorize: shape in bold cyan, node group(s) in dim gray
        shape_line = f"[bold cyan]{shape}[/]"
        ng_line = f"[bright_black]{ng_str}[/]" if ng_str else ""
        shape_ng_cell = f"{shape_line}\n{ng_line}" if ng_line else f"{shape_line}\n"
        # Try read training config (Any)
        model_str = "-"
        dataset_str = "-"
        try:
            trainer = getattr(spec, "trainer", None)
            tc = getattr(trainer, "train_config", None) if trainer else None
            if isinstance(tc, str):
                try:
                    tc = json.loads(tc)
                except Exception:
                    tc = None
            if isinstance(tc, dict):
                # Base model / model uri
                model_str = (
                    tc.get("model_uri")
                    or tc.get("base_model")
                    or tc.get("model")
                    or "-"
                )
                # Training dataset (top line)
                train_uri = tc.get("train_dataset_uri") or tc.get("dataset_uri")
                train_split = tc.get("train_dataset_split") or tc.get("dataset_split")
                train_line = (
                    f"{train_uri}{f' ({train_split})' if train_split else ''}"
                    if train_uri
                    else "-"
                )
                # Validation dataset (bottom line)
                val_uri = tc.get("validation_dataset_uri")
                val_split = tc.get("validation_dataset_split")
                val_line = (
                    f"{val_uri}{f' ({val_split})' if val_split else ''}"
                    if val_uri
                    else "-"
                )
                dataset_str = f"{train_line}\n{val_line}"
        except Exception:
            pass

        table.add_row(
            name_id_cell,
            created_ts,
            state_cell,
            owner or "-",
            shape_ng_cell,
            str(workers),
            model_str,
            dataset_str,
        )
    console.print(table)


@finetune.command(name="list")
@click.option(
    "-q", "--q", type=str, required=False, help="Substring match for job name."
)
@click.option("--query", type=str, required=False, help="Label selector query.")
@click.option(
    "--status", type=str, multiple=True, help="Filter by job state (repeatable)."
)
@click.option(
    "--node-group",
    "node_groups",
    type=str,
    multiple=True,
    help="Filter by node group (repeatable).",
)
@click.option(
    "--created-by", type=str, required=False, help="Filter by creator email (single)."
)
@click.option("--page", type=int, required=False, help="Page number (1-based).")
@click.option("--page-size", type=int, required=False, help="Items per page.")
@click.option(
    "--include-archived",
    "-ia",
    is_flag=True,
    default=False,
    help="Include archived jobs (alive_and_archive).",
)
def list_command(
    q: Optional[str],
    query: Optional[str],
    status: Optional[List[str]],
    node_groups: Optional[List[str]],
    created_by: Optional[str],
    page: Optional[int],
    page_size: Optional[int],
    include_archived: bool,
):
    """List finetune jobs."""
    client = APIClient()
    job_query_mode = (
        LeptonJobQueryMode.AliveAndArchive.value
        if include_archived
        else LeptonJobQueryMode.AliveOnly.value
    )
    jobs = client.finetune.list_all(
        job_query_mode=job_query_mode,
        q=q,
        query=query,
        status=list(status) if status else None,
        node_groups=list(node_groups) if node_groups else None,
        page=page,
        page_size=page_size,
        created_by=created_by or None,
    )
    _print_finetune_jobs_table(jobs, dashboard_base_url=client.get_dashboard_base_url())


@finetune.command(name="get")
@click.option("--id", "-i", type=str, required=True, help="Fine-tune job ID")
@click.option(
    "--include-archived",
    "-ia",
    is_flag=True,
    default=False,
    help="Include archived jobs when resolving the ID",
)
def get_command(id: str, include_archived: bool):
    """Get a finetune job by ID."""
    client = APIClient()
    job_query_mode = (
        LeptonJobQueryMode.AliveAndArchive.value
        if include_archived
        else LeptonJobQueryMode.AliveOnly.value
    )
    job = client.finetune.get(id, job_query_mode=job_query_mode)
    console.print(json.dumps(client.finetune.safe_json(job), indent=2))


@finetune.command(name="delete")
@click.option("--id", "-i", type=str, required=True, help="Fine-tune job ID")
@click.option(
    "--include-archived",
    "-ia",
    is_flag=True,
    default=False,
    help="Include archived jobs when resolving the ID",
)
def delete_command(id: str, include_archived: bool):
    """Delete a finetune job by ID."""
    client = APIClient()
    job_query_mode = (
        LeptonJobQueryMode.AliveAndArchive.value
        if include_archived
        else LeptonJobQueryMode.AliveOnly.value
    )
    client.finetune.get(id, job_query_mode=job_query_mode)
    client.finetune.delete(id, job_query_mode=job_query_mode)
    console.print(f"Finetune job [green]{id}[/] deleted successfully.")


@finetune.command(name="list-trainers")
def list_trainers_command():
    """List available finetune trainers."""
    client = APIClient()
    trainers = client.finetune.list_trainers()
    logger.trace(json.dumps(trainers[0].model_dump(), indent=2))
    table = Table(title="Trainers", show_header=True, show_lines=True)
    table.add_column("Trainer ID")
    table.add_column("Is Default")
    for t in trainers:
        table.add_row(
            getattr(t, "trainer_id", "-"),
            "Yes" if getattr(t, "is_default", False) else "",
        )
    console.print(table)


@finetune.command(name="list-supported-models")
def list_supported_models_command():
    """List supported models and techniques."""
    client = APIClient()
    models = client.finetune.list_supported_models()
    table = Table(title="Supported Models", show_header=True, show_lines=True)
    table.add_column("Model ID")
    table.add_column("SFT")
    table.add_column("LoRA")

    def _fmt(b: Optional[bool]) -> str:
        if b is None:
            return "-"
        return "[green]Yes[/]" if b else "[red]No[/]"

    for m in models:
        sft = getattr(getattr(m, "sft", None), "is_supported", None)
        lora = getattr(getattr(m, "lora", None), "is_supported", None)
        table.add_row(getattr(m, "model_id", "-"), _fmt(sft), _fmt(lora))
    console.print(table)


@finetune.command(name="create", cls=DynamicSchemaCommand)
@click.option(
    "--name",
    "-n",
    type=str,
    required=True,
    help="Finetune job name.",
)
@click.option(
    "-t",
    "--template",
    type=str,
    required=False,
    hidden=True,
    help=(
        "Template ID to derive parameters from (default: nemo-automodel). "
        "Use -h after setting this to see dynamic flags."
    ),
)
@click.option(
    "--resource-shape",
    "-rs",
    type=str,
    help="Resource shape for the pod.",
    default=None,
)
@click.option(
    "--num-workers",
    "-w",
    help="Number of workers to use for the job. For distributed execution, set > 1.",
    type=int,
    default=None,
)
@click.option(
    "--segment-count",
    type=int,
    default=None,
    help=(
        "Segment count (advanced). Must satisfy 1 <= segment_count < num_workers and "
        "num_workers % segment_count == 0."
    ),
)
@click.option(
    "--mount",
    multiple=True,
    help=(
        "Persistent storage to be mounted to the job, in the format"
        " `STORAGE_PATH:MOUNT_PATH` or `STORAGE_PATH:MOUNT_PATH:MOUNT_FROM`."
    ),
)
@click.option(
    "--shared-memory-size",
    type=int,
    help="Specify the shared memory size for this job, in MiB.",
)
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    type=str,
    multiple=True,
    help="Node group(s) for the job (repeatable).",
)
@click.option(
    "--node-id",
    "-ni",
    "node_ids",
    type=str,
    multiple=True,
    help="Specific node id(s) within the chosen node group(s) (repeatable).",
)
@click.option(
    "--queue-priority",
    "-qp",
    "queue_priority",
    callback=_validate_queue_priority,
    help=(
        "Set the priority for this job (dedicated node groups only). "
        "Examples: 1..9 or aliases like low/mid/high."
    ),
)
@click.option(
    "--can-be-preempted",
    "-cbp",
    is_flag=True,
    default=None,
    help="Allow this job to be preempted by higher priority jobs.",
)
@click.option(
    "--can-preempt",
    "-cp",
    is_flag=True,
    default=None,
    help="Allow this job to preempt lower priority jobs.",
)
@click.option(
    "--with-reservation",
    type=str,
    help="Use a specific reservation ID (dedicated node groups only).",
)
@click.option(
    "--allow-burst-to-other-reservation",
    is_flag=True,
    default=False,
    help="Allow burst to other reservation pools when available.",
)
@click.option(
    "--visibility",
    type=str,
    required=False,
    help="Visibility of the job. Can be 'public' or 'private'.",
)
def create_command(
    name: str,
    template: Optional[str],
    resource_shape: Optional[str],
    num_workers: Optional[int],
    segment_count: Optional[int],
    mount: Optional[List[str]],
    shared_memory_size: Optional[int],
    node_groups: Optional[List[str]],
    node_ids: Optional[List[str]],
    queue_priority: Optional[str],
    can_be_preempted: Optional[bool],
    can_preempt: Optional[bool],
    with_reservation: Optional[str],
    allow_burst_to_other_reservation: bool,
    visibility: Optional[str],
    **kwargs,
):
    """Create a finetune job (WIP). Dynamic flags are injected from the template schema."""

    job_params = {
        "name": name,
        "resource_shape": resource_shape,
        "num_workers": num_workers,
        "segment_count": segment_count,
        "mount": list(mount) if mount else None,
        "shared_memory_size": shared_memory_size,
        "node_groups": list(node_groups) if node_groups else None,
        "node_ids": list(node_ids) if node_ids else None,
        "queue_priority": queue_priority,
        "can_be_preempted": can_be_preempted,
        "can_preempt": can_preempt,
        "with_reservation": with_reservation,
        "allow_burst_to_other_reservation": allow_burst_to_other_reservation,
        "visibility": visibility,
    }
    trainer_flags: Dict[str, Any] = {k: v for k, v in kwargs.items() if v is not None}
    payload = {"trainer": {"train_config": trainer_flags}}
    logger.trace(json.dumps({"job_params": job_params, "payload": payload}, indent=2))

    spec = LeptonFineTuneJobSpec()
    if resource_shape:
        spec.resource_shape = resource_shape
    if num_workers is not None:
        if num_workers <= 0:
            console.print("[red]Error: --num-workers must be greater than 0.[/]")
            raise SystemExit(1)
        spec.completions = num_workers
        spec.parallelism = num_workers
        spec.intra_job_communication = True
    if segment_count is not None:
        err = None
        if not num_workers or num_workers <= 1:
            err = "--segment-count requires --num-workers > 1."
        elif not (1 <= segment_count < num_workers) or (
            num_workers % segment_count != 0
        ):
            err = "segment-count must be in [1, num_workers) and divide num_workers."
        if err:
            console.print(f"[red]Error[/]: {err}")
            raise SystemExit(1)
        spec.segment_config = LeptonJobSegmentConfig(
            count_per_segment=num_workers // segment_count
        )
    if shared_memory_size is not None:
        if shared_memory_size < 0:
            console.print("[red]Error: --shared-memory-size must be >= 0.[/]")
            raise SystemExit(1)
        spec.shared_memory_size = shared_memory_size
    if mount:
        try:
            spec.mounts = make_mounts_from_strings(mount)  # type: ignore
        except Exception as e:
            console.print(f"[red]Error parsing --mount[/]: {e}")
            raise SystemExit(1)
    try:
        apply_nodegroup_and_queue_config(
            spec=spec,
            node_groups=node_groups,
            node_ids=node_ids,
            queue_priority=queue_priority,
            can_be_preempted=can_be_preempted,
            can_preempt=can_preempt,
            with_reservation=with_reservation,
            allow_burst=allow_burst_to_other_reservation,
        )
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        raise SystemExit(1)
    # Attach trainer
    spec.trainer = Trainer(train_config=trainer_flags or None)

    job = LeptonFineTuneJob(
        metadata=Metadata(
            id=name,
            visibility=LeptonVisibility(visibility) if visibility else None,
        ),
        spec=spec,
    )
    client = APIClient()
    try:
        created = client.finetune.create(job)
        console.print(f"Finetune job [green]{created.metadata.id_}[/] created.")
        logger.trace(json.dumps(client.finetune.safe_json(created), indent=2))
    except Exception as e:
        console.print(f"[red]Failed to create finetune job[/]: {e}")
        raise SystemExit(1)


def add_command(cli_group):
    cli_group.add_command(finetune)
