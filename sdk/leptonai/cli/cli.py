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


if __name__ == "__main__":
    lep()
