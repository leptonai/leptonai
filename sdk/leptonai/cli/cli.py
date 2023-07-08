from . import deployment
from . import photon
from . import secret
from . import storage
from . import workspace
from .util import click_group

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click_group(context_settings=CONTEXT_SETTINGS)
def lep():
    """
    The main entry point for the Lepton AI SDK CLI.
    """
    pass


# Add subcommands
deployment.add_command(lep)
photon.add_command(lep)
secret.add_command(lep)
storage.add_command(lep)
workspace.add_command(lep)


if __name__ == "__main__":
    lep()
