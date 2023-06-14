import click
from .photon import cli as photon_cli
from .remote import cli as remote_cli

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
def lep():
    pass


photon_cli.add_command(lep)
remote_cli.add_command(lep)


if __name__ == "__main__":
    lep()
