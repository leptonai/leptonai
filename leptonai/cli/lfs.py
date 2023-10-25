"""
LFS is a module that provides a way to upload large files to the LeptonAI storage.
"""

import click
import os

import cloudpickle

from .util import (
    console,
    check,
    click_group,
)
from leptonai import Remote
from leptonai.util import lfs as util_lfs


@click_group()
def lfs():
    """
    [Note: LFS is still in beta. Expect lots of rough edges.]

    Utility to upload large files and folders to the Lepton AI cloud.

    The lfs commands allow you to upload large files and folders to the Lepton AI
    cloud. Unlike the `lep storage` commands, the lfs commands are designed to
    handle large files and folders, and can be used to resume upload if the
    upload is interrupted. Under the hood, it launches a remote photon that
    handles the upload.
    """
    pass


@lfs.command()
@click.argument("local_path", type=str)
@click.argument("remote_path", type=str, default="/")
@click.option(
    "--chunk-size",
    type=int,
    help="Chunk size to use for file upload",
    default=1024 * 1024 * 10,
)
def upload(local_path, remote_path, chunk_size):
    """
    Upload a local file or folder to the current workspace's storage. If `local_path` is a file, it will be uploadd to remote_path with the same name. If `local_path`
    is a folder, all the contents will be uploaded to remote_path.

    For example, if
    `local_path` is a folder `/foo/bar`, and has a file `baz.txt`, and `remote_path`
    is `/`, then the file will be uploaded to `/baz.txt`. If `remote_path` is `/foo`,
    then the file will be uploaded to `/foo/baz.txt`.

    The upload is done in chunks of size `chunk_size`. The default chunk size is 10MB.
    """
    if os.path.isfile(local_path):
        is_file = True
        remote_path = os.path.join(remote_path, os.path.basename(local_path))
    else:
        check(os.path.isdir(local_path), "Local path must be a file or a folder.")
        is_file = False

    console.print("Starting remote file server...")
    cloudpickle.register_pickle_by_value(util_lfs)
    r = Remote(
        util_lfs.ChunkedFileServer,
        mounts=[f"/:{util_lfs.DEFAULT_CHUNK_FILE_SERVER_UPLOAD_ROOT}"],
    )
    uploader = util_lfs.Uploader(r, chunk_size=chunk_size)
    console.print("Uploading...")
    if is_file:
        uploader.upload_file(local_path, remote_path)
    else:
        uploader.upload_folder(local_path, remote_path)


@lfs.command()
@click.argument("remote_path", type=str)
def rmdir(remote_path):
    """
    Remove a (nonempty) folder from the current workspace's storage. Only use this
    command if you are sure that you want to remove the file or folder. Also,
    if you are removing a folder with only a few files, use lep storage rm instead.
    """
    console.print("Starting remote file server...")
    cloudpickle.register_pickle_by_value(util_lfs)
    r = Remote(
        util_lfs.ChunkedFileServer,
        mounts=[f"/:{util_lfs.DEFAULT_CHUNK_FILE_SERVER_UPLOAD_ROOT}"],
    )
    console.print("Removing...")
    uploader = util_lfs.Uploader(r)
    uploader.delete_folder(remote_path)


def add_command(cli_group):
    cli_group.add_command(lfs)
