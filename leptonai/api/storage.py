import os
import requests
from typing import Optional

from .util import create_header, json_or_error, APIError


def _prepend_separator(file_path):
    """
    Utility function to add leading slash to relative paths if needed
    """
    return file_path if file_path.startswith("/") else "/" + file_path


def get_dir(url: str, auth_token: Optional[str], file_path: str):
    """
    Get the contents of a directory on the currently logged in remote server.
    :param str file_path: path to the directory on the remote server
    """
    response = requests.get(
        f"{url}/storage/default{_prepend_separator(file_path)}",
        headers=create_header(auth_token),
    )
    return json_or_error(response)


def check_file_type(url: str, auth_token: Optional[str], file_path: str):
    """
    Check if the contents at file_path stored on the remote server are a file or a directory.

    :param str file_path: path to the file or directory on the remote server

    Returns "file" or "dir" if the file exists, None otherwise.
    """
    # json output of get_dir does not include trailing separators
    file_path = file_path.rstrip(os.sep)
    file_path = _prepend_separator(file_path)
    parent_dir = "/" if os.path.dirname(file_path) == "" else os.path.dirname(file_path)

    parent_contents = get_dir(url, auth_token, parent_dir)
    if isinstance(parent_contents, APIError):
        return None

    base = os.path.basename(file_path)
    for item in parent_contents:
        if item["name"] == base:
            return item["type"]
    return None


def check_path_exists(url: str, auth_token: Optional[str], file_path: str):
    """
    Check if the contents at file_path exist on the remote server.

    :param str file_path: path to the file or directory on the remote server
    """

    req_url = f"{url}/storage/default{_prepend_separator(file_path)}"
    response = requests.head(req_url, headers=create_header(auth_token))
    return response.status_code == 200


def remove_file_or_dir(url: str, auth_token: Optional[str], file_path: str):
    """
    Remove a file or directory on the currently logged in remote server.

    :param str file_path: path to the file or directory on the remote server
    """
    req_url = f"{url}/storage/default{_prepend_separator(file_path)}"
    response = requests.delete(req_url, headers=create_header(auth_token))
    return response


def create_dir(url: str, auth_token: Optional[str], file_path: str):
    """
    Create a directory on the currently logged in remote server.
    :param str file_path: path to the directory on the remote server
    """
    req_url = f"{url}/storage/default{_prepend_separator(file_path)}"
    response = requests.put(req_url, headers=create_header(auth_token))
    return response


def upload_file(url: str, auth_token: Optional[str], local_path: str, remote_path: str):
    """
    Upload a file to the currently logged in remote server.

    :param str local_path: path to the file on the local machine
    :param str remote_path: path to the file on the remote server
    """
    req_url = f"{url}/storage/default{_prepend_separator(remote_path)}"
    with open(local_path, "rb") as file:
        response = requests.post(
            req_url, files={"file": file}, headers=create_header(auth_token)
        )
        return response


def download_file(
    url: str, auth_token: Optional[str], remote_path: str, local_path: str
):
    """
    Download a file from the currently logged in remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)
    :param str remote_path: path to the file on the remote server
    :param str local_path: absolute path to the file on the local machine
    """
    req_url = f"{url}/storage/default{_prepend_separator(remote_path)}"
    response = requests.get(req_url, headers=create_header(auth_token), stream=True)
    if response.status_code >= 200 and response.status_code <= 299:
        # download file
        try:
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        file.write(chunk)
        except Exception as e:
            print(f"Could not download file to {local_path}")
            (print(f"Error: {e}"))
            # We will return an APIError with the response status code 200,
            # but append the error message to the APIError message.
            err = APIError(response)
            err.message += (
                f"Could not download file to {local_path}. Encountered error: {e}"
            )
            return err
        # If success, we will return a json dict with key being name and value being
        # the local path to the file.
        return {"name": local_path}
    else:
        return APIError(response)
