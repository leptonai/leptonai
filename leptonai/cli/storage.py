import os

from rich.console import Console
from rich.theme import Theme
from .constants import STORAGE_DISPLAY_PREFIX_LAST, STORAGE_DISPLAY_PREFIX_MIDDLE
import click

from leptonai.api import storage as api

from .util import (
    check,
    click_group,
    guard_api,
    get_workspace_and_token_or_die,
    explain_response,
)

custom_theme = Theme(
    {
        "directory": "bold cyan",
    }
)

console = Console(highlight=False, theme=custom_theme)


def print_dir_contents(dir_path, dir_content_json):
    """
    Format the contents of a directory for printing.

    :param str dir_path: path to the parent directory

    :param list dir_json: list of files and directories in the parent directory
    """
    num_directories = 0
    num_files = 0
    for i, item in enumerate(dir_content_json):
        console.print(f"[directory]{dir_path}[/directory]") if i == 0 else None
        prefix = (
            STORAGE_DISPLAY_PREFIX_LAST
            if i == len(dir_content_json) - 1
            else STORAGE_DISPLAY_PREFIX_MIDDLE
        )
        if item["type"] == "dir":
            num_directories += 1
            msg = f'{prefix} [directory]{item["name"]}/[/directory]'
        else:
            num_files += 1
            msg = f'{prefix} {item["name"]}'
        console.print(msg)

    dir_tense = "directory" if num_directories == 1 else "directories"
    file_tense = "file" if num_files == 1 else "files"
    console.print(f"{num_directories} {dir_tense}, {num_files} {file_tense}")


@click_group()
def storage():
    pass


@storage.command()
@click.argument("path", type=str, default="/")
def ls(path):
    """
    List the contents of a directory of the current storage.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    check(
        api.check_path_exists(workspace_url, auth_token, path),
        f"[red]{path}[/] not found",
    )

    path_content = guard_api(
        api.get_dir(workspace_url, auth_token, path),
        detail=True,
        msg=f"ls [red]{path}[/] failed. See error message above.",
    )
    print_dir_contents(path, path_content)


@storage.command()
@click.argument("path", type=str)
def rm(path):
    """
    Delete a file stored in a PV on the currently logged in remote server.
    :param str path: relative path of the file or directory to delete
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    check(
        api.check_path_exists(workspace_url, auth_token, path),
        f"[red]{path}[/] not found.",
    )

    file_type = api.check_file_type(workspace_url, auth_token, path)
    check(file_type is not None, f"[red]{path}[/] not found")
    check(
        file_type != "dir",
        (
            f"[red]{path}[/] is a directory. Use [red]rmdir {path}[/] to delete"
            " directories."
        ),
    )

    explain_response(
        api.remove_file_or_dir(workspace_url, auth_token, path),
        f"Deleted [green]{path}[/].",
        f"[red]rm {path}[/] failed. See error above",
        f"[red]rm {path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("path", type=str)
def rmdir(path):
    workspace_url, auth_token = get_workspace_and_token_or_die()
    check(
        api.check_path_exists(workspace_url, auth_token, path),
        f"[red]{path}[/] not found",
    )

    file_type = api.check_file_type(workspace_url, auth_token, path)
    check(file_type is not None, f"[red]{path}[/] not found")
    check(
        file_type == "dir",
        f"[red]{path}[/] is a file. Use [red]rm {path}[/] to delete files.",
    )

    explain_response(
        api.remove_file_or_dir(workspace_url, auth_token, path),
        f"Deleted [green]{path}[/].",
        f"[red]rmdir {path}[/] failed. See error above.",
        f"[red]rmdir {path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("path", type=str)
def mkdir(path):
    """
    Create a directory on the currently logged in remote server.
    :param str path: relative path of the directory to create
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    explain_response(
        api.create_dir(workspace_url, auth_token, path),
        f"Created directory [green]{path}[/].",
        f"[red]mkdir {path}[/] failed. See error above.",
        f"[red]mkdir {path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("local_path", type=str)
@click.argument("remote_path", type=str, default="/")
def upload(local_path, remote_path):
    """
    Upload a file to the currently logged in remote server.
    :param str localpath: file path of the local file to upload
    :param str remotepath: absolute path of the remote file to create
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    # if the remote path is a directory, upload the file with its local name to that directory
    if remote_path[-1] == "/":
        remote_path = remote_path + local_path.split("/")[-1]

    explain_response(
        api.upload_file(workspace_url, auth_token, local_path, remote_path),
        f"Uploaded file [green]{local_path}[/] to [green]{remote_path}[/]",
        f"[red]upload {local_path} to {remote_path}[/] failed. See error above.",
        f"[red]upload {local_path} to {remote_path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("remote_path", type=str)
@click.argument("local_path", type=str, default="")
def download(remote_path, local_path):
    """
    Download a file from the currently logged in remote server.
    :param str remotepath: absolute path of the remote file to download
    :param str localpath: file path of the local file to create
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()

    check(
        api.check_path_exists(workspace_url, auth_token, remote_path),
        f"[red]{remote_path}[/] not found",
    )
    check(
        api.check_file_type(workspace_url, auth_token, remote_path) == "file",
        f"[red]{remote_path}[/] is not a file",
    )

    remote_file_name = remote_path.split("/")[-1]
    # handle no local path specified by using cwd
    if local_path == "":
        local_path = os.path.join(os.getcwd(), remote_file_name)
    # handle relative local paths by prepending the cwd
    if local_path[0] != os.sep:
        local_path = os.path.join(os.getcwd(), local_path)
    # if local path is a directory, download to that directory with the remote file name
    if os.path.isdir(local_path):
        local_path = os.path.join(local_path, remote_file_name)
    # check if local path's parent directory exists
    check(
        os.path.exists(os.path.dirname(local_path)),
        f"[red]local path {local_path} does not exist[/]",
    )

    guard_api(
        api.download_file(workspace_url, auth_token, remote_path, local_path),
        detail=True,
        msg=(
            f"[red]download {remote_path} to {local_path} failed[/]. See error message"
            " above."
        ),
    )
    console.print(f"Downloaded file [green]{remote_path}[/] to [green]{local_path}[/]")


def add_command(click_group):
    click_group.add_command(storage)


ALIASES = {
    "up": upload,
    "down": download,
    "dl": download,
}
