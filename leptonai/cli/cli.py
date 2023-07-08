import click

from . import deployment
from . import in_n_out
from . import photon
from . import secret
from . import storage
from . import workspace
from .util import click_group

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click_group(context_settings=CONTEXT_SETTINGS)
def lep():
    """
    The main entry point for the Lepton AI commandline interface.
    """
    pass


# Add subcommands
deployment.add_command(lep)
photon.add_command(lep)
secret.add_command(lep)
storage.add_command(lep)
workspace.add_command(lep)


@lep.command()
def login():
    """
    Login to the Lepton AI cloud.
    """
    in_n_out.cloud_login()


@lep.command()
def logout():
    """
    Logout of the Lepton AI cloud.
    """
    in_n_out.cloud_logout()


def _recursive_help(cmd, parent=None, parent_commands=None):
    """
    Recursively print help for all subcommands. This is used as an internal
    """
    ctx = click.core.Context(cmd, info_name=cmd.name, parent=parent)
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
        print(f"{'#' * len(commands)} {' '.join(commands)} ")
        print()
        print("```")
        print(cmd.get_help(ctx))
        print("```")
        print()
        sub_commands = getattr(cmd, "commands", {})
        for sub in sub_commands.values():
            _recursive_help(sub, parent=ctx, parent_commands=commands)


@lep.command(hidden=True)
def dump():
    """
    Internal command to dump help for all subcommands into markdown formats. This
    isn't usually being used by a regular end user, but is only a developer tool
    to generate the help pages. Hence this command is hidden from the daily CLI.
    """
    _recursive_help(lep)


if __name__ == "__main__":
    lep()
