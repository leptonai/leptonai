import click
from .photon import cli as photo_cli
from .remote import cli as remote_cli

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
def lepton():
    pass


photo_cli.add_command(lepton)
remote_cli.add_command(lepton)


if __name__ == "__main__":
    lepton()
