"""
Login is the main module that allows a serverless login.
"""
import webbrowser

from .util import check, console, guard_api, get_connection_or_die
from leptonai.api import workspace
from leptonai.api.connection import Connection

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
    workspace_id = workspace.get_workspace()
    if workspace_id and not credentials:
        # Already logged in. Notify the user the login status.
        conn = get_connection_or_die()
        console.print(
            "Hint: If you have multiple workspaces, you can pick the one you want\n"
            "to log in via `lep workspace login -i workspace_id`."
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
                    " [green]https://dashboard.lepton.ai/credentials[/] and copy it"
                    " over, or use `lep login -c \[credentials]` to log in."
                )
            while not credentials:
                credentials = input("Credential: ")

        workspace_id, auth_token = credentials.split(":", 1)
        url = workspace.get_full_workspace_api_url(workspace_id)
        check(url, "Workspace [red]{workspace_id}[/] does not exist.")
        workspace.save_workspace(workspace_id, url, auth_token=auth_token)
        workspace.set_current_workspace(workspace_id)
        conn = Connection(url, auth_token)
    # Try to login and print the info.
    info = workspace.get_workspace_info(conn)
    guard_api(
        info,
        detail=True,
        msg=(
            f"Cannot properly log into workspace [red]{workspace_id}."
            " This should usually not happen - it might be a transient"
            " network issue. Please contact us by sharing the error message above."
        ),
    )

    console.print(f"Logged in to your workspace [green]{workspace_id}[/].")
    console.print(f"\tbuild time: {info['build_time']}")
    console.print(f"\t   version: {info['git_commit']}")


def cloud_logout(purge=False):
    """
    Logs out of the serverless cloud.
    """
    if purge:
        workspace_id = workspace.get_workspace()
        workspace.remove_workspace(workspace_id)
        if workspace_id:
            console.print(
                f"OK, purging credentials for workspace [green]{workspace_id}[/]."
            )
    workspace.set_current_workspace(None)
    console.print("Logged out of Lepton AI.")
