import json
import os
import subprocess
import sys

from loguru import logger
from rich.console import Console
from rich.theme import Theme
from .constants import STORAGE_DISPLAY_PREFIX_LAST, STORAGE_DISPLAY_PREFIX_MIDDLE
import click

from .util import (
    click_group,
    sizeof_fmt,
    check,
    _get_only_replica_public_ip,
)
from ..api.v1.client import APIClient

custom_theme = Theme({
    "directory": "bold cyan",
})

console = Console(highlight=False, theme=custom_theme)


def print_dir_contents(dir_path, dir_infos):
    """
    Format the contents of a directory for printing.

    :param str dir_path: path to the parent directory

    :param list dir_json: list of files and directories in the parent directory
    """
    num_directories = 0
    num_files = 0
    for i, dir_info in enumerate(dir_infos):
        console.print(f"[directory]{dir_path}[/directory]") if i == 0 else None
        prefix = (
            STORAGE_DISPLAY_PREFIX_LAST
            if i == len(dir_infos) - 1
            else STORAGE_DISPLAY_PREFIX_MIDDLE
        )
        if dir_info.type == "dir":
            num_directories += 1
            msg = f"{prefix} [directory]{dir_info.name}/[/directory]"
        else:
            num_files += 1
            msg = f"{prefix} {dir_info.name}"
        console.print(msg)

    dir_tense = "directory" if num_directories == 1 else "directories"
    file_tense = "file" if num_files == 1 else "files"
    console.print(f"{num_directories} {dir_tense}, {num_files} {file_tense}")


@click_group()
def storage():
    """
    Manage File storage on the Lepton AI cloud.

    Lepton AI provides a file storage service that allows you to store files and
    directories on the cloud. The storage is persistent and is associated with
    your workspace. You can mount the storage when you launch a photon and
    access the files and directories from your photon code as if they were on
    a standard POSIX filesystem.

    The file commands allow you to list, upload, download, and delete files
    and directories in your workspace.
    """
    pass


@storage.command()
def du():
    """
    Returns total disk usage of the workspace
    """
    client = APIClient()

    file_system = client.storage.total_file_system_usage_bytes()

    logger.trace(json.dumps(client.job.safe_json(file_system), indent=2))

    humanized_usage = sizeof_fmt(file_system.status.total_usage_bytes)

    console.print(f"Total disk usage: {humanized_usage}")


@storage.command()
@click.argument("path", type=str, default="/")
def ls(path):
    """
    List the contents of a directory of the current file storage.
    """

    client = APIClient()
    check(
        client.storage.check_exists(path),
        f"[red]{path}[/] not found",
    )

    dir_infos = client.storage.get_dir(path)

    print_dir_contents(path, dir_infos)


@storage.command()
@click.argument("path", type=str)
def rm(path):
    """
    Delete a file in the file storage of the current workspace. Note that wildcard is
    not supported yet.
    """

    client = APIClient()

    check(
        client.storage.check_exists(path),
        f"[red]{path}[/] not found",
    )

    if (client.storage.get_file_type(path)) == "dir":
        console.print(
            f"[red]{path}[/] is a directory. Use [red]rmdir {path}[/] to delete"
            " directories."
        )
        sys.exit(1)

    client.storage.delete_file_or_dir(path)
    console.print(f"Deleted [green]{path}[/].")


@storage.command()
@click.argument("path", type=str)
def rmdir(path):
    """
    Delete a directory in the file storage of the current workspace. The directory
    must be empty. Note that wildcard is not supported yet.
    """

    client = APIClient()

    check(
        client.storage.check_exists(path),
        f"[red]{path}[/] not found",
    )

    if (client.storage.get_file_type(path)) != "dir":
        console.print(
            f"[red]{path}[/] is a file. Use [red]rm {path}[/] to delete files."
        )
        sys.exit(1)

    client.storage.delete_file_or_dir(path)
    console.print(f"Deleted [green]{path}[/].")


@storage.command()
@click.argument("path", type=str)
def mkdir(path):
    """
    Create a directory in the file storage of the current workspace.
    """

    client = APIClient()
    client.storage.create_dir(path)
    console.print(f"Created directory [green]{path}[/].")


@storage.command()
@click.argument("local_path", type=str)
@click.argument("remote_path", type=str, default="/")
@click.option(
    "--rsync",
    is_flag=True,
    help=(
        "Upload large files over 1 GBs with rsync for sustainability. Rsync is "
        "only available for standard and enterprise workspace plan. Add -p to show "
        "the progress."
    ),
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Upload directories recursively. Only supported with --rsync.",
)
@click.option(
    "--progress",
    "-p",
    is_flag=True,
    help="Show progress. Only supported with --rsync.",
)
def upload(local_path, remote_path, rsync, recursive, progress):
    """
    Upload a local file to the storage of the current workspace. If remote_path
    is not specified, the file will be uploaded to the root directory of the
    storage. If remote_path is a directory, you need to append a "/", and the
    file will be uploaded to that directory with its local name.
    """
    # if the remote path is a directory, upload the file with its local name to that directory
    client = APIClient()

    if remote_path[-1] == "/":
        remote_path = remote_path + local_path.split("/")[-1]

    if recursive and not rsync:
        console.print("Cannot use --recursive without --rsync")
        sys.exit(1)
    if progress and not rsync:
        console.print("Cannot use --progress without --rsync")
        sys.exit(1)

    if rsync:
        console.print(
            f"Uploading file(or directory) [green]{local_path}[/] to"
            f" [green]{remote_path}[/] with rsync..."
        )

        name = "storage-rsync-by-lepton"

        lepton_deployment = client.deployment.get(name)
        port = lepton_deployment.spec.container.ports[0].host_port
        ip = _get_only_replica_public_ip(name)

        workspace_id = client.get_workspace_id()

        pwd = client.token()
        if len(pwd) > 8:
            pwd = pwd[:8]
        env_vars = {"RSYNC_PASSWORD": pwd}
        flags = "-v"
        if recursive:
            flags += "a"
        if progress:
            flags += " --progress"
        command = (
            f"rsync {flags}"
            f" {local_path} rsync://{workspace_id}@{ip}:{port}/volume{remote_path}"
        )
        console.print(f"Running command: [bold]{command}[/]")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env_vars,
            shell=True,
            universal_newlines=True,
        )

        for line in process.stdout:
            print(line, end="")
        process.wait()

        return

    client.storage.create_file(local_path, remote_path)
    console.print(f"Uploaded file [green]{local_path}[/] to [green]{remote_path}[/]")


@storage.command()
@click.argument("remote_path", type=str)
@click.argument("local_path", type=str, default="")
def download(remote_path, local_path):
    """
    Download a remote file. If no local path is specified, the file will be
    downloaded to the current working directory with the same name as the remote
    file.
    """
    client = APIClient()
    check(
        client.storage.check_exists(remote_path),
        f"[red]{remote_path}[/] not found",
    )

    if client.storage.get_file_type(remote_path) != "file":
        console.print(f"[red]{remote_path}[/] is not a file")
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
    check(
        os.path.exists(os.path.dirname(local_path)),
        f"[red]local path {local_path} does not exist[/]",
    )

    client.storage.get_file(remote_path, local_path)
    console.print(f"Downloaded file [green]{remote_path}[/] to [green]{local_path}[/]")


def add_command(click_group):
    # Backward compatibility: if users stil call "lep storage", keep it working.
    click_group.add_command(storage)
    click_group.add_command(storage, name="file")
