"""Launcher for lep-tui, the terminal UI for DGX Cloud Lepton.

lep-tui is a standalone Bun-compiled binary released from the platform
monorepo to a GitLab generic package registry that allows anonymous pulls
(NVIDIA network or VPN required, no credentials). `lep tui` stays a thin
orchestrator on purpose:

- a first install runs the official ``install.sh`` so the blessed install
  path (platform probe, checksum verification, macOS re-signing, atomic
  rename into ``~/.local/bin``) has exactly one implementation, and
- updates delegate to the binary's own ``lep-tui update``, which owns the
  staging logic and the state behind ``lep-tui rollback``.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import click

from .util import console

# Keep in sync with apps/tui/scripts/install.sh and src/update/registry.ts in
# the platform monorepo; its RELEASING.md lists the places this URL lives.
TUI_REGISTRY_URL = (
    "https://gitlab-master.nvidia.com/api/v4/projects/186903/packages/generic/lep-tui"
)
TUI_BINARY_NAME = "lep-tui"

# lep-tui's environment contract (apps/tui src/auth/resolve.ts): the workspace
# and token must be set together, and credentials arriving this way run an
# ephemeral session — lep-tui never writes them into its own config file.
TUI_ENV_WORKSPACE = "LEPTON_WORKSPACE"
TUI_ENV_TOKEN = "LEPTON_AUTH_TOKEN"
TUI_ENV_GATEWAY = "LEPTON_API_URL"
# lep-tui refuses to start on a token without a gateway-routable prefix
# (src/auth/credentials.ts), so such a token must not be handed over at all —
# launching without it lands on the TUI's own login instead.
TUI_TOKEN_PREFIXES = ("nvapi-", "lapi-")


def _cli_auth_env() -> Optional[Dict[str, str]]:
    """Project the CLI's current workspace into lep-tui's env contract.

    Returns None when there is nothing safe to hand over: the caller already
    exported the TUI's variables, no workspace is logged in, or the token is
    of a shape lep-tui would refuse.
    """
    if TUI_ENV_WORKSPACE in os.environ or TUI_ENV_TOKEN in os.environ:
        return None
    from ..api.v2.workspace_record import WorkspaceRecord

    workspace_id = WorkspaceRecord.get_current_workspace_id()
    info = WorkspaceRecord.current()
    if not workspace_id or info is None or not info.auth_token:
        return None
    if not info.auth_token.startswith(TUI_TOKEN_PREFIXES):
        return None
    overrides = {TUI_ENV_WORKSPACE: workspace_id, TUI_ENV_TOKEN: info.auth_token}
    if info.url:
        # A full workspace API URL is fine here: lep-tui normalizes it down
        # to the gateway origin.
        overrides[TUI_ENV_GATEWAY] = info.url
    return overrides


def _default_install_dir() -> Path:
    return Path.home() / ".local" / "bin"


def _find_tui_binary() -> Optional[str]:
    """Locate lep-tui on PATH, falling back to the installer's default dir."""
    found = shutil.which(TUI_BINARY_NAME)
    if found:
        return found
    candidate = _default_install_dir() / TUI_BINARY_NAME
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def _install_tui(version: Optional[str]) -> str:
    """Run the official installer and return the installed binary path."""
    import requests

    label = f"version {version}" if version else "the latest release"
    source = (
        f"{TUI_REGISTRY_URL}/{version}/install.sh"
        if version
        else f"{TUI_REGISTRY_URL}/latest/install.sh"
    )
    console.print(f"lep-tui is not installed; installing {label}...")
    try:
        response = requests.get(source, timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        raise click.ClickException(
            f"Could not download the lep-tui installer from {source}"
            f" ({error}). lep-tui is distributed on the NVIDIA network —"
            " check your network or VPN."
        )
    handle = tempfile.NamedTemporaryFile(
        "w", prefix="lep-tui-install.", suffix=".sh", delete=False
    )
    try:
        with handle:
            handle.write(response.text)
        argv = ["sh", handle.name]
        if version:
            argv += ["--version", version]
        completed = subprocess.run(argv, check=False)
    finally:
        os.unlink(handle.name)
    if completed.returncode:
        raise click.ClickException(
            "The lep-tui installer failed; see its output above."
        )
    binary = _find_tui_binary()
    if not binary:
        raise click.ClickException(
            f"The installer finished but {TUI_BINARY_NAME} was found neither"
            f" on PATH nor in {_default_install_dir()}."
        )
    return binary


def _update_tui(binary: str, version: Optional[str]) -> None:
    """Self-update in place; a failure only skips the update, never the run."""
    argv = [binary, "update"]
    if version:
        argv += ["--target", version]
    completed = subprocess.run(argv, check=False)
    if completed.returncode:
        console.print(
            "[yellow]lep-tui self-update failed; launching the installed"
            " version.[/yellow]"
        )


@click.command(name="tui", context_settings={"ignore_unknown_options": True})
@click.option(
    "--no-update",
    is_flag=True,
    default=False,
    help="Launch the installed lep-tui without the pre-launch update.",
)
@click.option(
    "--tui-version",
    help="Install or update to a specific lep-tui version (prereleases too).",
)
@click.option(
    "--no-auth",
    is_flag=True,
    default=False,
    help=(
        "Do not sign lep-tui in as the CLI's current workspace; use"
        " lep-tui's own logins."
    ),
)
@click.argument("tui_args", nargs=-1, type=click.UNPROCESSED)
def tui(
    no_update: bool,
    tui_version: Optional[str],
    no_auth: bool,
    tui_args: Tuple[str, ...],
):
    """Launch lep-tui, installing or updating it first.

    lep-tui is the terminal UI for DGX Cloud Lepton. Installing and
    updating needs the NVIDIA network or VPN but no credentials. When the
    CLI is logged into a workspace, lep-tui starts signed in to it for
    this session only. Unknown arguments are passed through, e.g. `lep
    tui --mock` or `lep tui jobs`; use `--` before flags lep and lep-tui
    both understand.
    """
    if sys.platform.startswith("win"):
        raise click.UsageError(
            "lep-tui ships macOS and Linux builds only; Windows is not supported."
        )
    if no_update and tui_version:
        raise click.UsageError(
            "--tui-version needs the install/update step; drop --no-update."
        )
    binary = _find_tui_binary()
    if binary is None:
        binary = _install_tui(tui_version)
    elif not no_update:
        _update_tui(binary, tui_version)
    launch_env = None
    if not no_auth:
        overrides = _cli_auth_env()
        if overrides:
            console.print(
                "Signing lep-tui in as the CLI's current workspace"
                f" [green]{overrides[TUI_ENV_WORKSPACE]}[/] (session only;"
                " lep-tui's own logins stay untouched)."
            )
            launch_env = {**os.environ, **overrides}
    completed = subprocess.run([binary, *tui_args], check=False, env=launch_env)
    if completed.returncode:
        raise click.exceptions.Exit(completed.returncode)


def add_command(cli_group: click.Group) -> None:
    cli_group.add_command(tui)
