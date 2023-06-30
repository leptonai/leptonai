from .photon import cli as photon_cli
from .workspace import cli as workspace_cli
from .secret import cli as secret_cli
from .deployment import cli as deployment_cli
from .util import click_group

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click_group(context_settings=CONTEXT_SETTINGS)
def lep():
    pass


photon_cli.add_command(lep)
workspace_cli.add_command(lep)
secret_cli.add_command(lep)
deployment_cli.add_command(lep)


if __name__ == "__main__":
    lep()
