from rich.table import Table
import json
import sys
import click

from .util import (
    console,
    click_group,
    resolve_save_path,
    PathResolutionError,
    LooseChoice,
    keyword_matches,
    normalize_keyword,
)
from ..api.v2.client import APIClient

# Workload types offered by the dashboard's template filter ("pod", "job"); the
# CLI also lists endpoint templates, whose API spelling is "deployment".
TEMPLATE_WORKLOAD_FILTER_VALUES = ("pod", "job", "endpoint", "deployment")


def _filter_templates(templates, *, keyword=None, workloads=()):
    """Apply the template list filters; different filters are combined with AND."""
    normalized_keyword = normalize_keyword(keyword)
    wanted_workloads = {
        "deployment" if str(w).lower() == "endpoint" else str(w).lower()
        for w in workloads or ()
    }

    def matches(template):
        meta = getattr(template, "metadata", None)
        spec = getattr(template, "spec", None)
        if not keyword_matches(
            normalized_keyword,
            getattr(meta, "name", None) if meta else None,
            getattr(meta, "id_", None) if meta else None,
        ):
            return False
        if wanted_workloads:
            workload = (getattr(spec, "workload_type", None) if spec else None) or ""
            if workload.lower() not in wanted_workloads:
                return False
        return True

    return [template for template in templates if matches(template)]


@click_group()
def template():
    """Manage templates (list only)."""
    pass


@template.command(name="list")
@click.option(
    "--search",
    "--keyword",
    "-q",
    "keyword",
    type=str,
    help="Case-insensitive substring search across template name and ID.",
)
@click.option(
    "--workload",
    "-w",
    "workloads",
    type=LooseChoice(TEMPLATE_WORKLOAD_FILTER_VALUES),
    multiple=True,
    help=(
        "Filter by workload type ('endpoint' and 'deployment' are equivalent)."
        " Repeat for OR."
    ),
)
@click.option(
    "--public", "public_only", is_flag=True, help="List only public templates."
)
@click.option(
    "--private", "private_only", is_flag=True, help="List only private templates."
)
def list_command(keyword=None, workloads=(), public_only=False, private_only=False):
    """List all templates with Name/ID/Workload type.

    --search matches the template name or ID and --workload filters by workload
    type (as in the dashboard); --public/--private restrict the listing to one
    template collection. Different filters are combined with AND.
    """
    if public_only and private_only:
        raise click.UsageError("--public and --private are mutually exclusive.")

    client = APIClient()
    public_items = [] if private_only else client.template.list_public()
    private_items = [] if public_only else client.template.list_private()

    has_filters = any([keyword, workloads])
    public_items = _filter_templates(public_items, keyword=keyword, workloads=workloads)
    private_items = _filter_templates(
        private_items, keyword=keyword, workloads=workloads
    )
    if has_filters and not public_items and not private_items:
        console.print("[yellow]No templates match the specified filters.[/yellow]")
        return

    table = Table(title="Templates", show_lines=True)
    table.add_column("Name / ID")
    table.add_column("Workload")

    def _emit(items):
        for t in items:
            meta = t.metadata
            spec = t.spec
            if not meta:
                table.add_row("[bold]-[/]\n[dim]-[/]", "")
                continue
            tid = meta.id_ or meta.name or "-"
            name = meta.name or meta.id_ or "-"
            wl = (getattr(spec, "workload_type", None) or "").lower()
            wl_disp = "endpoint" if wl == "deployment" else wl
            # Keep colors consistent with resource-shape: pod=green, endpoint=cyan, job=magenta
            if wl_disp == "pod":
                wl_cell = "[green]pod[/]"
            elif wl_disp == "endpoint":
                wl_cell = "[cyan]endpoint[/]"
            elif wl_disp == "job":
                wl_cell = "[magenta]job[/]"
            else:
                wl_cell = wl_disp
            table.add_row(f"[bold]{name}[/]\n[dim]{tid}[/]", wl_cell)

    _emit(public_items)
    _emit(private_items)

    console.print(table)


@template.command(name="get", hidden=True)
@click.option("--id", "-i", type=str, required=True, help="Template ID to retrieve.")
@click.option(
    "--public", is_flag=True, default=False, help="Get from public templates."
)
@click.option(
    "--private", is_flag=True, default=False, help="Get from private templates."
)
@click.option(
    "--path",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    default=None,
    show_default=False,
    help="Optional local path to save the template JSON.",
)
def get_command(id: str, public: bool, private: bool, path: str | None):
    """Get a template by ID. If --path is set, save JSON to file.

    Namespace selection:
    - If --public is set, fetch from public.
    - If --private is set, fetch from private.
    - If neither is set, auto-detect by checking public first; if not found, use private.
    """
    if public and private:
        console.print("[red]Cannot specify both --public and --private.[/red]")
        sys.exit(1)

    client = APIClient()
    ns = "auto"
    try:
        if public:
            tpl = client.template.get_public(id)
            ns = "public"
        elif private:
            tpl = client.template.get_private(id)
            ns = "private"
        else:
            pubs = client.template.list_public()
            in_public = any(t.metadata and t.metadata.id_ == id for t in pubs)
            if in_public:
                tpl = client.template.get_public(id)
                ns = "public"
            else:
                tpl = client.template.get_private(id)
                ns = "private"
    except Exception as e:
        console.print(f"[red]Failed to get template '{id}':[/] {e}")
        sys.exit(1)

    data = tpl.model_dump() if hasattr(tpl, "model_dump") else tpl.dict()

    if path:
        try:
            path = resolve_save_path(path, f"template_{id}.json")
        except PathResolutionError as e:
            console.print(f"[red]Failed to save template: {e}[/]")
            sys.exit(1)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]Saved template ({ns}) to:[/bold green] {path}")
    else:
        console.print_json(data=data)


def add_command(cli_group):
    cli_group.add_command(template)
