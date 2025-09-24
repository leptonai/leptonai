from rich.table import Table

from .util import console, click_group
from ..api.v2.client import APIClient


@click_group()
def template():
    """Manage templates (list only)."""
    pass


@template.command(name="list")
def list_command():
    """List all templates with Name/ID/Workload type."""
    client = APIClient()
    public_items = client.template.list_public()
    private_items = client.template.list_private()

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


def add_command(cli_group):
    cli_group.add_command(template)
