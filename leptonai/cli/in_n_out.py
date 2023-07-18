"""
Login is the main module that allows a serverless login.
"""
import webbrowser

from .util import console, guard_api
from leptonai.api import workspace
from leptonai.util import get_full_workspace_api_url

LOGIN_LOGO = """\
========================================================
[blue]    _     _____ ____ _____ ___  _   _       _    ___     [/]
[blue]   | |   | ____|  _ \\_   _/ _ \\| \\ | |     / \\  |_ _|    [/]
[blue]   | |   |  _| | |_) || || | | |  \\| |    / _ \\  | |     [/]
[blue]   | |___| |___|  __/ | || |_| | |\\  |   / ___ \\ | |     [/]
[blue]   |_____|_____|_|    |_| \\___/|_| \\_|  /_/   \\_\\___|    [/]
                                                         
========================================================"""


def cloud_login(credentials=None):
    """
    Logs in to the serverless cloud.
    """
    console.print(LOGIN_LOGO)
    current_workspace = workspace.get_workspace()
    if current_workspace and not credentials:
        # Already logged in. Notify the user the login status.
        console.print(f"Logged in to your workspace [green]{current_workspace}[/].")
        console.print(
            "If you have multiple workspaces, use `lep workspace login -n \[name]` to"
            " pick the one you want to log in to."
        )
    else:
        # Need to login.
        if not credentials:
            # obtain credentials first.
            console.print(
                "Welcome to Lepton AI. We will open a browser for you to obtain your"
                " login credentials. Please log in with your registered account."
            )
            console.print(
                "You'll then be presented with your CLI credentials. If you have"
                " multiple workspaces, there will be multiple credentials - select the"
                " one you want to log in to. Copy the credential and paste it here."
            )
            input("Whenever you are ready, press Enter to continue...")

            success = webbrowser.open("https://dashboard.lepton.ai/credentials")
            if not success:
                console.print(
                    "It seems that you are running in a non-GUI environment. You can"
                    " manually obtain credentials from"
                    " https://dashboard.lepton.ai/credentials and copy it over, or use"
                    " `lep login -c \[credentials]` to log in."
                )
            while not credentials:
                credentials = input("Credential: ")

        workspace_name, auth_token = credentials.split(":", 1)
        url = get_full_workspace_api_url(workspace_name)
        workspace.save_workspace(workspace_name, url, auth_token=auth_token)
        workspace.set_current_workspace(workspace_name)
        guard_api(
            workspace.get_workspace_info(url, auth_token),
            detail=True,
            msg=(
                f"Cannot properly log into workspace [red]{workspace_name}. This should"
                " usually not happen - it might be a transient network issue. Please"
                " contact us by sharing the error message above."
            ),
        )
        console.print(f"Logged in to your workspace [green]{workspace_name}[/].")


def cloud_logout(purge=False):
    """
    Logs out of the serverless cloud.
    """
    if purge:
        name = workspace.get_workspace()
        workspace.remove_workspace(name)
        if name:
            console.print(f"OK, purging credentials for workspace [green]{name}[/].")
    workspace.set_current_workspace(None)
    console.print("Logged out of Lepton AI.")
