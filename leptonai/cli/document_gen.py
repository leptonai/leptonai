import os
from pathlib import Path
from typing import Sequence, Tuple

import click
from click.formatting import HelpFormatter
from loguru import logger

from .util import console


class CliReferenceFormatter(HelpFormatter):
    """
    A custom formatter for the Lepton AI CLI reference into Markdown formats.
    """
    def __init__(self, *args, **kwargs):
        HelpFormatter.__init__(self, *args, **kwargs)

    def write_usage(self, prog: str, args: str = "", prefix: str | None = None) -> None:
        """
        Writes the usage line into the buffer.
        """
        self.write_heading("Usage")
        self.write(f"`{prog} {args}`")
        self.write("\n")

    def write_heading(self, heading: str) -> None:
        """
        Writes a heading into the buffer.
        """
        self.write("\n")
        self.write(f"### {heading}")
        self.write("\n")

    def write_dl(
        self, rows: Sequence[Tuple[str, str]], col_max: int = 30, col_spacing: int = 2
    ) -> None:
        """
        Writes a definition list into the buffer.
        """
        for first, second in rows:
            if "," in first:
                # This is an option like "-o, --option TEXT", so we split it
                # and display each single option in a code block.
                short, long = first.split(",", 1)
                first = f"{short}`, `{long}"
            self.write(f"- `{first}` : {second}")
            self.write("\n")
        self.write("\n")

    def write_text(self, text: str) -> None:
        return super().write_text(text)


def _format_lepton_help(cmd, ctx):
    formatter = CliReferenceFormatter(
        width=ctx.terminal_width, max_width=ctx.max_content_width
    )
    cmd.format_help_text(ctx, formatter)
    cmd.format_usage(ctx, formatter)
    cmd.format_options(ctx, formatter)
    cmd.format_epilog(ctx, formatter)
    return formatter.getvalue().rstrip("\n")


def _recursive_help(cmd, parent=None, parent_commands=None, stop=False):
    ctx = click.core.Context(cmd, info_name=cmd.name, parent=parent)
    ctx.formatter_class = CliReferenceFormatter
    commands = (
        parent_commands
        + [
            cmd.name,
        ]
        if parent_commands
        else [
            cmd.name,
        ]
    )
    if not cmd.hidden:
        title = f"\n{'#' * max(len(commands)-1, 1)} {' '.join(commands)}\n"
        content = _format_lepton_help(cmd, ctx)
        if stop:
            return "\n\n".join([title, content])
        else:
            sub_contents = []
            sub_commands = getattr(cmd, "commands", {})
            for sub in sub_commands.values():
                if not sub.hidden:
                    sub_contents.append(
                        _recursive_help(sub, parent=ctx, parent_commands=commands)
                    )
            return "\n".join([title, content] + sub_contents)


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_documentation_file(
    file_path: Path, content: str, frontmatter: str = None
) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        if frontmatter:
            f.write("---\n")
            f.write(frontmatter)
            f.write("---\n\n")
        f.write(content)


def _get_page_path(base_dir: Path, subdir: str, extension: str) -> Path:
    if subdir:
        return base_dir / subdir / f"page.{extension}"
    return base_dir / f"page.{extension}"


@click.command(hidden=True)
@click.option(
    "--root", "-f", default=".", help="The repo root to dump the help files into."
)
@click.option(
    "--extension", "-e", default="mdx", help="The file extension to use for the files."
)
def dump(root: str, extension: str):
    from .cli import lep
    
    # Setup output directory
    output_dir = Path(root) / "references"
    console.print(f"Dumping help pages into markdown files under [blue]{output_dir}[/].")
    _ensure_directory(output_dir)
    
    # Generate the main lep page
    main_page = _recursive_help(lep, stop=True)
    main_page_path = _get_page_path(output_dir, "", extension)
    frontmatter = "description: Lepton Commandline Interface (CLI) reference\n"
    _write_documentation_file(main_page_path, main_page, frontmatter)
    
    # Generate subcommand pages
    sub_commands = getattr(lep, "commands", {})
    root_ctx = click.core.Context(lep, info_name=lep.name, parent=None)
    logger.info(f"Found {len(sub_commands)} subcommands: {sub_commands.keys()}.")
    
    for name, sub in sub_commands.items():
        if not sub.hidden:
            page_content = _recursive_help(sub, parent=root_ctx, parent_commands=[lep.name])
            subdir_name = f"lep_{name}"
            subdir_path = output_dir / subdir_name
            _ensure_directory(subdir_path)
            page_path = _get_page_path(output_dir, subdir_name, extension)
            _write_documentation_file(page_path, page_content)


def add_command(cli_group):
    cli_group.add_command(dump)

