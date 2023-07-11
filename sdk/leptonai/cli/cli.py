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
    Lep is the main entry point for the Lepton AI commandline interface. It provides
    a set of commands to create and develop photons locally, and deploy them to the
    Lepton AI cloud. It also provides a set of commands to manage resources on the
    cloud, such as workspaces, deployments, secrets, and storage.
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
    Login to the Lepton AI cloud. This will open a browser window to the Lepton AI
    login page. After logging in, you will be redirected to a page with an access
    code. Copy the access code and paste it into the terminal, and you will be
    logged in.
    """
    in_n_out.cloud_login()


@lep.command()
@click.option(
    "--forget", is_flag=True, help="Forget the credentials of the lepton login info."
)
def logout(forget):
    """
    Logout of the Lepton AI cloud.
    """
    in_n_out.cloud_logout(forget=forget)


if __name__ == "__main__":
    lep()
