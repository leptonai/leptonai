import os
import subprocess
import sys

from loguru import logger
from rich.console import Console
from rich.theme import Theme
from .constants import STORAGE_DISPLAY_PREFIX_LAST, STORAGE_DISPLAY_PREFIX_MIDDLE
import click

from leptonai.api import storage as api
from leptonai.api import deployment as deploymentapi
from leptonai.api.workspace import WorkspaceInfoLocalRecord

from .util import (
    check,
    click_group,
    guard_api,
    get_connection_or_die,
    explain_response,
    sizeof_fmt,
    get_only_replica_public_ip_or_die,
)

custom_theme = Theme({
    "directory": "bold cyan",
})

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
    conn = get_connection_or_die()
    usage = guard_api(
        api.du(conn),
        detail=True,
        msg="du failed. See error message above.",
    )
    logger.trace(usage)
    humanized_usage = sizeof_fmt(usage["totalDiskUsageBytes"])
    console.print(f"Total disk usage: {humanized_usage}")


@storage.command()
@click.argument("path", type=str, default="/")
def ls(path):
    """
    List the contents of a directory of the current file storage.
    """
    conn = get_connection_or_die()
    check(
        api.check_path_exists(conn, path),
        f"[red]{path}[/] not found",
    )

    path_content = guard_api(
        api.get_dir(conn, path),
        detail=True,
        msg=f"ls [red]{path}[/] failed. See error message above.",
    )
    print_dir_contents(path, path_content)


@storage.command()
@click.argument("path", type=str)
def rm(path):
    """
    Delete a file in the file storage of the current workspace. Note that wildcard is
    not supported yet.
    """
    conn = get_connection_or_die()
    check(
        api.check_path_exists(conn, path),
        f"[red]{path}[/] not found.",
    )

    file_type = api.check_file_type(conn, path)
    check(file_type is not None, f"[red]{path}[/] not found")
    check(
        file_type != "dir",
        f"[red]{path}[/] is a directory. Use [red]rmdir {path}[/] to delete"
        " directories.",
    )

    explain_response(
        api.remove_file_or_dir(conn, path),
        f"Deleted [green]{path}[/].",
        f"[red]rm {path}[/] failed. See error above",
        f"[red]rm {path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("path", type=str)
def rmdir(path):
    """
    Delete a directory in the file storage of the current workspace. The directory
    must be empty. Note that wildcard is not supported yet.
    """
    conn = get_connection_or_die()
    check(
        api.check_path_exists(conn, path),
        f"[red]{path}[/] not found",
    )

    file_type = api.check_file_type(conn, path)
    check(file_type is not None, f"[red]{path}[/] not found")
    check(
        file_type == "dir",
        f"[red]{path}[/] is a file. Use [red]rm {path}[/] to delete files.",
    )

    explain_response(
        api.remove_file_or_dir(conn, path),
        f"Deleted [green]{path}[/].",
        f"[red]rmdir {path}[/] failed. See error above.",
        f"[red]rmdir {path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("path", type=str)
def mkdir(path):
    """
    Create a directory in the file storage of the current workspace.
    """
    conn = get_connection_or_die()
    explain_response(
        api.create_dir(conn, path),
        f"Created directory [green]{path}[/].",
        f"[red]mkdir {path}[/] failed. See error above.",
        f"[red]mkdir {path}[/] failed. Internal service error.",
    )


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

        conn = get_connection_or_die()

        name = "storage-rsync-by-lepton"
        dep_info = guard_api(
            deploymentapi.get_deployment(conn, name),
            detail=True,
            msg="Cannot obtain info for [red]rsync service[/]. See error above.",
        )
        port = dep_info["container"]["ports"][0]["host_port"]
        ip = get_only_replica_public_ip_or_die(conn, name)

        workspace = WorkspaceInfoLocalRecord.get_current_workspace_id()
        pwd = WorkspaceInfoLocalRecord.get_current_workspace_token()
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
            f" {local_path} rsync://{workspace}@{ip}:{port}/volume{remote_path}"
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

    conn = get_connection_or_die()
    explain_response(
        api.upload_file(conn, local_path, remote_path),
        f"Uploaded file [green]{local_path}[/] to [green]{remote_path}[/]",
        f"[red]upload {local_path} to {remote_path}[/] failed. See error above.",
        f"[red]upload {local_path} to {remote_path}[/] failed. Internal service error.",
    )


@storage.command()
@click.argument("remote_path", type=str)
@click.argument("local_path", type=str, default="")
def download(remote_path, local_path):
    """
    Download a remote file. If no local path is specified, the file will be
    downloaded to the current working directory with the same name as the remote
    file.
    """
    conn = get_connection_or_die()

    check(
        api.check_path_exists(conn, remote_path),
        f"[red]{remote_path}[/] not found",
    )
    check(
        api.check_file_type(conn, remote_path) == "file",
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
        api.download_file(conn, remote_path, local_path),
        detail=True,
        msg=(
            f"[red]download {remote_path} to {local_path} failed[/]. See error message"
            " above."
        ),
    )
    console.print(f"Downloaded file [green]{remote_path}[/] to [green]{local_path}[/]")


def add_command(click_group):
    # Backward compatibility: if users stil call "lep storage", keep it working.
    click_group.add_command(storage)
    click_group.add_command(storage, name="file")
