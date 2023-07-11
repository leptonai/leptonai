"""
Login is the main module that allows a serverless login.
"""
import webbrowser

from .util import console
from leptonai.api import workspace
from leptonai.util import get_full_workspace_api_url

LOGIN_LOGO = """\
========================================================
[blue]    _     _____ ____ _____ ___  _   _       _    ___     [/]
[blue]   | |   | ____|  _ \\_   _/ _ \\| \\ | |     / \\  |_ _|    [/]
[blue]   | |   |  _| | |_) || || | | |  \\| |    / _ \\  | |     [/]
[blue]   | |___| |___|  __/ | || |_| | |\\  |   / ___ \\ | |     [/]
[blue]   |_____|_____|_|    |_| \\___/|_| \\_|  /_/   \\_\\___|    [/]
                                                         
========================================================
"""


def cloud_login():
    """
    Logs in to the serverless cloud.
    """
    console.print(LOGIN_LOGO)
    current_workspace = workspace.get_workspace()
    if current_workspace:
        console.print(f"Logged in to your workspace [green]{current_workspace}[/].")
    else:
        # Need to login.
        # TODO: I expect this function to be something like "open a browser asking
        # the user to log in. After log in, we display the connection string, and
        # then ask the user to paste it back here, and we parse the string to get
        # the workspace name and auth token.
        # For now, this page is not implemented yet.
        raise RuntimeError("This is not implemented yet. Stay tuned.")
        console.print("Welcome to Lepton AI cloud. Let's log you in.")
        console.print(
            "We will open a browser for you to obtain your workspace "
            "and auth token for your commandline interface."
        )
        console.print("In the browser, please log in to your Lepton AI account.")
        console.print(
            "After logging in, you will be redirected to a page with "
            "your workspace connection string."
        )
        console.print("Please copy the connection string and paste it here.")
        input("Whenever you are ready, press Enter to continue...")
        webbrowser.open("https://login.lepton.ai/?redirect=credentials")
        console.print("[green]Connection string:[/] ")

        connection_string = input("")
        workspace_name, auth_token = connection_string.split(":", 1)
        # TODO: sanity check the workspace name and auth token.
        url = get_full_workspace_api_url(workspace_name)
        workspace.save_workspace(workspace_name, url, auth_token=auth_token)
        console.print("Logged in to your workspace [green]{workspace_name}[/].")


def cloud_logout(forget=False):
    """
    Logs out of the serverless cloud.
    """
    if forget:
        name = workspace.get_workspace()
        workspace.remove_workspace(name)
        if name:
            console.print(f"Forgot credentials for workspace [green]{name}[/].")
    workspace.set_current_workspace(None)
    console.print("Logged out of Lepton AI cloud.")
