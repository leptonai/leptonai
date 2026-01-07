import json
import sys
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
    resolve_save_path,
    PathResolutionError,
)
from ..api.v2.client import APIClient
from leptonai.api.v1.types.job import LeptonJobQueryMode, LeptonJobSegmentConfig
from leptonai.api.v1.types.common import Metadata, LeptonVisibility
from leptonai.api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from leptonai.config import VALID_SHAPES
from leptonai.api.v2.types.finetune import (
    LeptonFineTuneJob,
    LeptonFineTuneJobSpec,
    Trainer,
)
from .util import _ValidatedCommand


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
        except Exception as e:
            console.print(
                f"[red]Failed to fetch training template[/]: {template_id} ({e})"
            )
            raise e
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


class DynamicSchemaCommand(_ValidatedCommand):
    """A Click command that injects options at runtime from a template's json_schema."""

    _generated_for_template: Optional[str] = None

    def make_context(self, info_name, args, parent=None, **extra):
        if not self._has_file_arg(args):
            try:
                default_template_id = (
                    APIClient().finetune.list_trainers(default_only=True)[0].trainer_id
                )
            except Exception:
                default_template_id = "nemo-automodel"
            template_id = self._parse_template_arg(args) or default_template_id
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
    def _has_file_arg(args: List[str]) -> bool:
        for i, a in enumerate(args):
            if a in ("-f", "--file") and i + 1 < len(args):
                return True
            if a.startswith("--file="):
                return True
        return False

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
            raw_type = prop.get("type", "string")
            # Normalize union types like ["integer", "null"] to their primary non-null type
            if isinstance(raw_type, list):
                non_null_types = [t for t in raw_type if t != "null"]
                ptype = non_null_types[0] if non_null_types else "string"
            else:
                ptype = raw_type
            addl = prop.get("additionalProperties")
            is_string_mapping = (
                ptype == "object"
                and isinstance(addl, dict)
                and addl.get("type") == "string"
            )
            trainer_tag = "[trainer]"
            param_decls: Any
            if ptype == "boolean":
                param_decls = (f"{flag(name)}/--no-{name.replace('_','-')}",)
                option_kwargs = {
                    "help": f"{trainer_tag} {(desc or '').strip()}",
                }
                if default is not None:
                    option_kwargs["default"] = bool(default)
                    option_kwargs["show_default"] = True
                options.append(click.Option(param_decls, **option_kwargs))
            elif ptype == "integer":
                option_kwargs = {
                    "type": int,
                    "required": name in required,
                    "help": f"{trainer_tag} {(desc or '').strip()}",
                }
                if default is not None:
                    option_kwargs["default"] = default
                    option_kwargs["show_default"] = True
                options.append(click.Option((flag(name),), **option_kwargs))
            elif ptype == "number":
                option_kwargs = {
                    "type": float,
                    "required": name in required,
                    "help": f"{trainer_tag} {(desc or '').strip()}",
                }
                if default is not None:
                    option_kwargs["default"] = default
                    option_kwargs["show_default"] = True
                options.append(click.Option((flag(name),), **option_kwargs))
            else:
                if is_string_mapping:
                    options.append(
                        click.Option(
                            (flag(name),),
                            type=str,
                            multiple=True,
                            required=name in required,
                            callback=_parse_kv_list,
                            help=f"{trainer_tag} "
                            + (
                                ((desc + " — ") if desc else "")
                                + "repeatable KEY:VALUE (e.g., question:prompt)"
                            ),
                            show_default=False,
                        )
                    )
                else:
                    option_kwargs = {
                        "type": str,
                        "required": name in required,
                        "help": f"{trainer_tag} " + (
                            (desc or "")
                            + (" (JSON)" if ptype in ("object", "array") else "")
                        ),
                    }
                    if default is not None:
                        option_kwargs["default"] = default
                        option_kwargs["show_default"] = True
                    options.append(click.Option((flag(name),), **option_kwargs))
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
@click.option(
    "--path",
    "-p",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    required=False,
    help=(
        "Optional local path to save the job spec JSON. Directory or full filename "
        "accepted. If a directory is provided, the file will be saved as "
        "finetune-job-spec-<job_id>.json."
    ),
)
def get_command(id: str, include_archived: bool, path: Optional[str]):
    """Get a finetune job by ID."""
    client = APIClient()
    job_query_mode = (
        LeptonJobQueryMode.AliveAndArchive.value
        if include_archived
        else LeptonJobQueryMode.AliveOnly.value
    )
    job = client.finetune.get(id, job_query_mode=job_query_mode)
    console.print(json.dumps(client.finetune.safe_json(job), indent=2))
    if path:
        job_spec_json = job.spec.model_dump_json(indent=2, by_alias=True)
        try:
            save_path = resolve_save_path(
                path, f"finetune-job-spec-{job.metadata.id_}.json"
            )
        except PathResolutionError as e:
            console.print(f"[red]Failed to save job spec: {e}[/]")
            sys.exit(1)
        try:
            with open(save_path, "w") as f:
                f.write(job_spec_json)
            console.print(f"Job spec saved to [green]{save_path}[/].")
        except Exception as e:
            console.print(f"[red]Failed to save job spec: {e}[/]")
            sys.exit(1)


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


@finetune.command(name="list-trainers", hidden=True)
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


@finetune.command(name="create", cls=DynamicSchemaCommand)
@click.option(
    "--name",
    "-n",
    type=str,
    required=True,
    help="[job] Finetune job name.",
)
@click.option(
    "-t",
    "--template",
    type=str,
    required=False,
    hidden=True,
    help=(
        "Template ID to derive parameters from (default: nemo-automodel). Use -h after"
        " setting this to see dynamic flags. will be ignored in --file mode."
    ),
)
@click.option(
    "--resource-shape",
    "-rs",
    type=str,
    help="[job] Resource shape for the finetune job.",
    default=None,
)
@click.option(
    "--num-workers",
    "-w",
    help=(
        "[job] Number of workers to use for the job. For distributed execution, set"
        " > 1."
    ),
    type=int,
    default=None,
)
@click.option(
    "--segment-count",
    help=(
        "[job] Segment count for GB200 node groups. Must satisfy: 1 <= segment_count <"
        " num_workers, and num_workers % segment_count == 0. Workers within the same"
        " segment are scheduled into one NVL72 domain."
    ),
    type=int,
    default=None,
)
@click.option(
    "--mount",
    multiple=True,
    help=(
        "[job] Persistent storage to be mounted to the job, in the format"
        "`STORAGE_PATH:MOUNT_PATH:MOUNT_FROM`."
    ),
)
@click.option(
    "--shared-memory-size",
    type=int,
    help="[job] Specify the shared memory size for this job, in MiB.",
)
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    help=(
        "[job] Node group for the job. You can repeat"
        " this flag multiple times to choose multiple node groups. Multiple node group"
        " option is currently not supported but coming soon for enterprise users. Only"
        " the first node group will be set if you input multiple node groups at this"
        " time."
    ),
    type=str,
    multiple=True,
)
@click.option(
    "--node-id",
    "-ni",
    "node_ids",
    help=(
        "[job] Node for the job. You can repeat this flag multiple times to choose"
        " multiple nodes. Please specify the node group when you are using this option"
    ),
    type=str,
    multiple=True,
)
@click.option(
    "--queue-priority",
    "-qp",
    "queue_priority",
    callback=_validate_queue_priority,
    help=(
        "[job] Set the priority for this job (feature available only for dedicated node"
        " groups).\nCould be one of low-1, low-2, low-3, mid-4, mid-5, mid-6,"
        " high-7, high-8, high-9,Options: 1-9 or keywords: l / low (will be 1), m /"
        " mid (will be 4), h / high (will be 7).\nExamples: -qp 1, -qp 9, -qp low,"
        " -qp mid, -qp high, -qp l, -qp m, -qp h"
    ),
)
@click.option(
    "--can-be-preempted",
    "-cbp",
    is_flag=True,
    default=None,
    help="[job] Allow this job to be preempted by higher priority jobs.",
)
@click.option(
    "--can-preempt",
    "-cp",
    is_flag=True,
    default=None,
    help="[job] Allow this job to preempt lower priority jobs.",
)
@click.option(
    "--with-reservation",
    type=str,
    help=(
        "[job] Assign the job to a specific reserved compute resource using a"
        " reservation ID (only applicable to dedicated node groups). If not provided,"
        " the job will be scheduled as usual."
    ),
)
@click.option(
    "--allow-burst-to-other-reservation",
    is_flag=True,
    default=False,
    help=(
        "[job] If set, the job can temporarily use free resources from nodes reserved"
        " by other reservations. Be aware that when a new workload bound to those"
        " reservations starts, your job may be evicted."
    ),
)
@click.option(
    "--visibility",
    type=str,
    required=False,
    help="[job] Visibility of the job. Can be 'public' or 'private'.",
)
@click.option(
    "--file",
    "-f",
    help=(
        "Load finetune job spec from JSON file, then allow job-related CLI options to"
        " override it. Note: in --file mode, trainer parameters are NOT injected;"
        " dynamic trainer options are unavailable (unknown options will error). To"
        " change trainer settings, please edit the spec file.Use `lep finetune get -i"
        " <job_id> --path <download_path>` to download the spec file of existing"
        " finetune job."
    ),
    type=str,
    required=False,
)
@click.option(
    "--hf-token",
    type=str,
    required=False,
    help=(
        "[trainer] Secret name for Hugging Face token (NOT the token value). "
        "Create it in Workspace Settings -> Secrets or via `lep secret create`. "
        "This option injects env 'HF_TOKEN' referencing that secret."
    ),
)
@click.option(
    "--wandb-api-key",
    type=str,
    required=False,
    help=(
        "[trainer] Secret name for Weights & Biases API key (NOT the raw key). "
        "Create it in Workspace Settings -> Secrets or via `lep secret create`. "
        "This option injects env 'WANDB_API_KEY' referencing that secret."
    ),
)
@click.pass_context
def create_command(
    ctx: click.Context,
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
    file: Optional[str],
    hf_token: Optional[str],
    wandb_api_key: Optional[str],
    **kwargs,
):
    """Create a finetune job."""

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
    trainer_payload = {"trainer": {"train_config": trainer_flags}}
    logger.trace(
        json.dumps({"job_params": job_params, "trainer": trainer_payload}, indent=2)
    )

    # Load base spec from file if provided
    if file:
        try:
            with open(file, "r") as f:
                content = f.read()
                spec = LeptonFineTuneJobSpec.parse_raw(content)
        except Exception as e:
            console.print(f"[red]Cannot load finetune spec from file[/]: {file} ({e})")
            sys.exit(1)
    else:
        spec = LeptonFineTuneJobSpec()

    # Apply simple presence-based overrides (no defaults for job params)
    if resource_shape is not None:
        spec.resource_shape = resource_shape
    if num_workers is not None:
        if num_workers <= 0:
            console.print("[red]Error: --num-workers must be greater than 0.[/]")
            sys.exit(1)
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
            sys.exit(1)
        spec.segment_config = LeptonJobSegmentConfig(
            count_per_segment=num_workers // segment_count
        )
    if shared_memory_size is not None:
        if shared_memory_size < 0:
            console.print("[red]Error: --shared-memory-size must be >= 0.[/]")
            sys.exit(1)
        spec.shared_memory_size = shared_memory_size
    if mount:
        try:
            spec.mounts = make_mounts_from_strings(mount)  # type: ignore
        except Exception as e:
            console.print(f"[red]Error parsing --mount[/]: {e}")
            sys.exit(1)
    fixed_secrets: List[str] = []
    if hf_token:
        fixed_secrets.append(f"HF_TOKEN={hf_token}")
    if wandb_api_key:
        fixed_secrets.append(f"WANDB_API_KEY={wandb_api_key}")
    if fixed_secrets:
        injected = make_env_vars_from_strings(env=None, secret=fixed_secrets)
        if injected:
            spec.envs = (spec.envs or []) + injected
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
        sys.exit(1)
    if not spec.resource_shape:
        available_types = "\n      ".join(VALID_SHAPES)
        console.print(
            "[red]Error: Missing option '--resource-shape'.[/] "
            f"Available types are:\n      {available_types} \n"
        )
        sys.exit(1)
    # Trainer: in file mode, do not override; warn if CLI trainer flags present
    if file:
        if trainer_flags:
            console.print(
                "[yellow]Warning[/]: using --file; CLI trainer parameters are ignored."
            )
        # keep spec.trainer as loaded from file
    else:
        spec.trainer = Trainer(train_config=trainer_flags or None)

    job = LeptonFineTuneJob(
        metadata=Metadata(
            id=name,
            visibility=LeptonVisibility(visibility) if visibility else None,
        ),
        spec=spec,
    )
    logger.trace(json.dumps(job.model_dump(), indent=2))
    client = APIClient()
    try:
        created = client.finetune.create(job)
        console.print(f"Finetune job [green]{created.metadata.id_}[/] created.")
        logger.trace(json.dumps(client.finetune.safe_json(created), indent=2))
    except Exception as e:
        console.print(f"[red]Failed to create finetune job[/]: {e}")
        sys.exit(1)


def add_command(cli_group):
    cli_group.add_command(finetune)
