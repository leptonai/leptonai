from datetime import datetime

import click
import sys
import webbrowser

from leptonai.api.v2.utils import WorkspaceUnauthorizedError, WorkspaceNotFoundError
from .util import console
from leptonai.api.v2.workspace_record import WorkspaceRecord
from loguru import logger

import leptonai
from . import deployment, node
from . import job
from . import kv
from . import objectstore
from . import photon
from . import pod
from . import queue
from . import secret
from . import storage
from . import workspace
from . import ingress
from . import log

from .util import click_group

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
LOGIN_LOGO = """

                            [#76B900]N V I D I A[/]

                        [white] D G X  C L O U D[/]

        [#76B900]██╗     ███████╗██████╗ ████████╗ ██████╗ ███╗   ██╗[/]
        [#76B900]██║     ██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗████╗  ██║[/]
        [#76B900]██║     █████╗  ██████╔╝   ██║   ██║   ██║██╔██╗ ██║[/]
        [#76B900]██║     ██╔══╝  ██╔═══╝    ██║   ██║   ██║██║╚██╗██║[/]
        [#76B900]███████╗███████╗██║        ██║   ╚██████╔╝██║ ╚████║[/]
        [#76B900]╚══════╝╚══════╝╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═══╝[/]


"""


@click.version_option(leptonai.__version__, "-v", "--version")
@click_group(context_settings=CONTEXT_SETTINGS)
def lep():
    """
    Lep is the main entry point for the Lepton AI commandline interface. It provides
    a set of commands to create and develop photons locally, and deploy them to the
    Lepton AI cloud. It also provides a set of commands to manage resources on the
    cloud, such as workspaces, deployments, secrets, and storage. To intall it, run

    `pip install -U leptonai`
    """
    pass


# Add subcommands
deployment.add_command(lep)
job.add_command(lep)
kv.add_command(lep)
objectstore.add_command(lep)
photon.add_command(lep)
pod.add_command(lep)
queue.add_command(lep)
secret.add_command(lep)
storage.add_command(lep)
workspace.add_command(lep)
node.add_command(lep)

ingress.add_command(lep)
log.add_command(lep)


@lep.command()
@click.option(
    "--credentials",
    "-c",
    help="The credentials of the lepton login info.",
    default=None,
)
@click.option(
    "--workspace-url",
    "-u",
    help="The url of the workspace to login to.",
    default=None,
)
@click.option(
    "--lepton-classic",
    "-l",
    is_flag=True,
    help="Login to the classic Lepton AI workspace.",
)
@click.option(
    "--workspace-origin-url",
    "-o",
    help="The origin url of the workspace to login to.",
    hidden=True,
    default=None,
)
def login(credentials, workspace_url, lepton_classic, workspace_origin_url):
    """
    Login to the Lepton AI cloud. This will open a browser window to the Lepton AI
    login page if credentials are not given. You will be redirected to a page with
    the credentials string. Copy the string and paste it into the terminal, and
    you will be logged in.
    """
    console.print(LOGIN_LOGO)
    need_further_login = False
    if credentials:
        workspace_id, auth_token = credentials.split(":", 1)
        WorkspaceRecord.set_or_exit(
            workspace_id,
            auth_token=auth_token,
            url=workspace_url,
            workspace_origin_url=workspace_origin_url,
            is_lepton_classic=lepton_classic,
        )
    else:
        if WorkspaceRecord.current():
            # Already logged in. Notify the user the login status.
            current_ws = WorkspaceRecord.current()
            # Note: Set LOGURU_LEVEL=TRACE to see these debug logs
            logger.trace(
                f"Current workspace info:\n  id: {current_ws.id_}\n  url:"
                f" {current_ws.url}\n  display_name: {current_ws.display_name}\n "
                " auth_token:"
                f" {current_ws.auth_token[:2]}****{current_ws.auth_token[-2:] if current_ws.auth_token else None}\n"
                f"  workspace_origin_url: {current_ws.workspace_origin_url}\n "
                f" is_lepton_classic: {current_ws.is_lepton_classic}"
            )
        else:
            candidates = WorkspaceRecord.workspaces()
            if len(candidates) == 0:
                need_further_login = True
            elif len(candidates) == 1:
                # Only one workspace, so we will simply log in to that one.
                ws = candidates[0]
                WorkspaceRecord.set_or_exit(ws.id_, ws.auth_token, ws.url, ws.workspace_origin_url, ws.is_lepton_classic)  # type: ignore
            else:
                # multiple workspaces. login to one of them.
                console.print("You have multiple workspaces. Please select one:")
                for i, ws in enumerate(candidates):
                    console.print(f"{i+1}. {ws.id_} ({ws.display_name})")
                choice = None
                while not choice:
                    choice = input("choice: ")
                try:
                    choice = int(choice) - 1
                except ValueError:
                    console.print("Invalid choice. Please enter a number.")
                    sys.exit(1)
                WorkspaceRecord.set_or_exit(
                    candidates[choice].id_,  # type: ignore
                    candidates[choice].auth_token,
                    candidates[choice].url,
                    candidates[choice].workspace_origin_url,
                    candidates[choice].is_lepton_classic,
                )
                console.print(
                    "Hint: If you have multiple workspaces, you can pick the one you"
                    " want\nto log in via `lep workspace login -i workspace_id`."
                )
    if need_further_login:
        # there is no credentials, and no current workspace. Will need to ask the
        # user to login interactively.
        # obtain credentials first.
        console.print(
            "\n[bold]Welcome to [#76B900]DGX Cloud Lepton[/][/bold]\n"
            "We will open a browser for you to obtain your login credentials.\n"
            "Please log in with your registered account.\n"
        )
        console.print(
            "[bold]Instructions:[/bold]\n"
            "1. A browser window will open to the workspace credentials page\n"
            "2. If you have multiple workspaces, select the one you want to log in to\n"
            "3. Copy the credential and paste it here\n"
            "4. The credential should be in the format:"
            " [#76B900]<workspace_id>:<auth_token>[/]\n"
        )
        input("Press Enter to continue...")

        credentials_page_url = "https://dashboard.dgxc-lepton.nvidia.com/credentials"
        if lepton_classic:
            credentials_page_url = "https://dashboard.lepton.ai/credentials"

        success = webbrowser.open(credentials_page_url)
        if not success:
            console.print(
                "It seems that you are running in a non-GUI environment. You can"
                " manually obtain credentials from"
                " [green]https://dashboard.lepton.ai/credentials[/] and copy it"
                r" over, or use `lep login -c \[credentials]` to log in."  # noqa: W605
            )
        while not credentials:
            credentials = input("Credential: ")
            if ":" not in credentials:
                credentials = None
                console.print(
                    "[red]A credential should be formatted as"
                    " <workspace_id>:<auth_token>[/]"
                )
        workspace_id, auth_token = credentials.split(":", 1)
        WorkspaceRecord.set_or_exit(workspace_id, auth_token=auth_token)
    # Try to login and print the info.
    api_client = WorkspaceRecord.client()

    try:
        info = api_client.info()
        console.print(f"Logged in to your workspace [blue]{info.workspace_name}[/].")
        console.print(f"\t      tier: {info.workspace_tier}")
        console.print(f"\tbuild time: {info.build_time}")
        console.print(f"\t   version: {api_client.version()}")

    except WorkspaceUnauthorizedError as e:
        console.print("\n", e)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"""
        [bold]Invalid Workspace Access Detected[/]
        [white]Workspace ID:[/white] {e.workspace_id}

        [white]Note: If you are trying to login to a Lepton classic workspace, please use:[/white]
        [#76B900]'lep login -c <workspace-id>:<token> --lepton-classic'[/#76B900]
        [white]Make sure to include the --lepton-classic or -l flag.[/white]

        [bold]To resolve this issue:[/bold]
        1. [#76B900]Verify your login credentials above.[/#76B900]

        [white]If using 'lep login' and encountering this error, you might be logging in with
        an invalid local credential.[/white]
        2. [white]To directly login, use:[/white]
            [#76B900]'lep login -c <workspace_id>:<auth_token>'[/#76B900]

        3. [white]Or list and remove the invalid local workspace credential with:[/white]
            [#76B900]'lep workspace list'[/#76B900]
            [#76B900]'lep workspace remove -i <workspace_id>'[/#76B900]
            [white]Then, log in again with:[/white]
            [#76B900]'lep login'[/#76B900]

        4. [#76B900]If the workspace was just created, please wait for 5 - 10 minutes.[/#76B900]
           [red]Contact us if the workspace remains unavailable after 10 minutes.[/red]
           (Current Time: [bold]{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}[/bold])
        """)

    except WorkspaceNotFoundError as e:
        console.print("\n", e)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"""
        [red bold]Workspace Not Found[/]
        [red]Workspace ID:[/red] {e.workspace_id}

        [bold]To resolve this issue:[/bold]
        1. [green]If the workspace was just created, please wait for 10 minutes. [/green]
           [yellow]Contact us if the workspace remains unavailable after 10 minutes.[/yellow]
           (Current Time: [bold blue]{current_time}[/bold blue])
        2. [green]Please check the login info you just used above[/green]
        3. [yellow]Login to the workspace with valid credentials:[/yellow]
           [green]lep workspace login -i <valid_workspace_id> -t <valid_workspace_token>[/green]
        """)


@lep.command()
@click.option(
    "--purge", is_flag=True, help="Purge the credentials of the lepton login info."
)
def logout(purge):
    """
    Logout of the Lepton AI cloud.
    """
    WorkspaceRecord.logout(purge=purge)
    console.print("[green]Logged out[/]")


if __name__ == "__main__":
    lep()
