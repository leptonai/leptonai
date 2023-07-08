from rich.console import Console
from rich.theme import Theme
from leptonai.api import storage as api
from .constants import STORAGE_DISPLAY_PREFIX_LAST, STORAGE_DISPLAY_PREFIX_MIDDLE
import os
import sys
import click

from leptonai.api import workspace
from .util import click_group

custom_theme = Theme(
    {
        "directory": "bold cyan",
    }
)

console = Console(highlight=False, theme=custom_theme)


def must_get_remote_url():
    url = workspace.get_current_workspace_url()
    if url is not None:
        return url
    console.print(
        "Not logged in to a remote server. Please log in using lep remote login"
    )
    sys.exit(1)


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
    List the contents of a directory of a PV on .
    :param str path:
    (e.g. http://localhost:8000)
    """
    url = must_get_remote_url()
    if not api.check_path_exists(url, path):
        console.print(f"[bold red]{path} not found[/]")
        sys.exit(1)

    response = api.get_dir(url, path)
    if not response:
        console.print(f"ls [red]{path}[/] failed")
        sys.exit(1)
    print_dir_contents(path, response.json())


@storage.command()
@click.argument("path", type=str)
def rm(path):
    """
    Delete a file stored in a PV on the currently logged in remote server.
    :param str path: relative path of the file or directory to delete
    """
    url = must_get_remote_url()
    if not api.check_path_exists(url, path):
        console.print(f"[bold red]{path} not found[/]")
        sys.exit(1)

    file_type = api.check_file_type(url, path)
    if file_type is None:
        console.print(f"[bold red]{path} not found[/]")
        sys.exit(1)
    if file_type == "dir":
        console.print(f"[bold red]{path} is a directory[/]")
        console.print(f"Use [bold red]rmdir {path}[/] to delete directories")
        sys.exit(1)

    if not api.remove_file_or_dir(url, path):
        console.print(f"[bold red]rm {path} failed[/]")
        sys.exit(1)
    console.print(f"Deleted {path}")


@storage.command()
@click.argument("path", type=str)
def rmdir(path):
    url = must_get_remote_url()
    if not api.check_path_exists(url, path):
        console.print(f"[bold red]{path} not found[/]")
        sys.exit(1)

    file_type = api.check_file_type(url, path)
    if file_type is None:
        console.print(f"[bold red]{path} not found[/]")
        sys.exit(1)
    if file_type == "file":
        console.print(f"[bold red]{path} is a file[/]")
        console.print(f"Use [bold red]rm {path}[/] to delete files")
        sys.exit(1)

    if not api.remove_file_or_dir(url, path):
        console.print(f"[bold red]rmdir {path} failed[/]")
        sys.exit(1)
    console.print(f"Deleted {path}")


@storage.command()
@click.argument("path", type=str)
def mkdir(path):
    """
    Create a directory on the currently logged in remote server.
    :param str path: relative path of the directory to create
    """
    url = must_get_remote_url()
    if not api.create_dir(url, path):
        console.print(f"[bold red]mkdir {path} failed[/]")
        sys.exit(1)
    console.print(f"Created directory [green]{path}[/]")


@storage.command()
@click.argument("local_path", type=str)
@click.argument("remote_path", type=str, default="/")
def upload(local_path, remote_path):
    """
    Upload a file to the currently logged in remote server.
    :param str localpath: file path of the local file to upload
    :param str remotepath: absolute path of the remote file to create
    """
    url = must_get_remote_url()
    # if the remote path is a directory, upload the file with its local name to that directory
    if remote_path[-1] == "/":
        remote_path = remote_path + local_path.split("/")[-1]

    if not api.upload_file(url, local_path, remote_path):
        console.print(f"[bold red]upload {local_path} to {remote_path} failed[/]")
        sys.exit(1)
    console.print(f"Uploaded file [green]{local_path}[/] to [green]{remote_path}[/]")


@storage.command()
@click.argument("remote_path", type=str)
@click.argument("local_path", type=str, default="")
def download(remote_path, local_path):
    """
    Download a file from the currently logged in remote server.
    :param str remotepath: absolute path of the remote file to download
    :param str localpath: file path of the local file to create
    """
    url = must_get_remote_url()

    if not api.check_path_exists(url, remote_path):
        console.print(f"[bold red]{remote_path} not found[/]")
        sys.exit(1)
    if not api.check_file_type(url, remote_path) == "file":
        console.print(f"[bold red]{remote_path} is not a file[/]")
        sys.exit(1)

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
    if not os.path.exists(os.path.dirname(local_path)):
        console.print(f"[bold red]local path {local_path} does not exist[/]")
        sys.exit(1)

    if not api.download_file(url, remote_path, local_path):
        console.print(f"[bold red]download {remote_path} to {local_path} failed[/]")
        sys.exit(1)
    console.print(f"Downloaded file [green]{remote_path}[/] to [green]{local_path}[/]")


def add_command(click_group):
    click_group.add_command(storage)


ALIASES = {
    "up": upload,
    "down": download,
    "dl": download,
}
