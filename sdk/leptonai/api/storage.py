from leptonai.util import create_header, check_and_print_http_error
from leptonai.api import workspace
import requests
import os


def get_dir(remote_url, file_path):
    """
    Get the contents of a directory on the currently logged in remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)
    :param str file_path: path to the directory on the remote server
    """
    req_url = f"{remote_url}/storage/default{prepend_separator(file_path)}"
    auth_token = workspace.get_auth_token(remote_url)
    response = requests.get(req_url, headers=create_header(auth_token))
    if check_and_print_http_error(response):
        return None
    return response


def check_file_type(remote_url, file_path):
    """
    Check if the contents at file_path stored on the remote server are a file or a directory.

    :param str remote_url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)

    :param str file_path: path to the file or directory on the remote server

    Returns "file" or "dir" if the file exists, None otherwise.
    """
    # json output of get_dir does not include trailing separators
    file_path = file_path.rstrip(os.sep)
    file_path = prepend_separator(file_path)
    parent_dir = "/" if os.path.dirname(file_path) == "" else os.path.dirname(file_path)

    response = get_dir(remote_url, parent_dir)
    if not response:
        return None

    parent_contents = response.json()
    base = os.path.basename(file_path)
    for item in parent_contents:
        if item["name"] == base:
            return item["type"]
    return None


def check_path_exists(remote_url, file_path):
    """
    Check if the contents at file_path exist on the remote server.

    :param str remote_url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)

    :param str file_path: path to the file or directory on the remote server
    """

    req_url = f"{remote_url}/storage/default{prepend_separator(file_path)}"
    auth_token = workspace.get_auth_token(remote_url)
    response = requests.head(req_url, headers=create_header(auth_token))
    return response.status_code == 200


def remove_file_or_dir(remote_url, file_path):
    """
    Remove a file or directory on the currently logged in remote server.
    :param str remote_url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)
    :param str file_path: path to the file or directory on the remote server
    """
    req_url = f"{remote_url}/storage/default{prepend_separator(file_path)}"
    auth_token = workspace.get_auth_token(remote_url)
    response = requests.delete(req_url, headers=create_header(auth_token))
    if response.status_code == 404:
        return False
    if check_and_print_http_error(response):
        return False
    return True


def create_dir(remote_url, file_path):
    """
    Create a directory on the currently logged in remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)
    :param str file_path: path to the directory on the remote server
    """
    req_url = f"{remote_url}/storage/default{prepend_separator(file_path)}"
    auth_token = workspace.get_auth_token(remote_url)
    response = requests.put(req_url, headers=create_header(auth_token))
    if check_and_print_http_error(response):
        return False
    return True


def upload_file(remote_url, local_path, remote_path):
    """
    Upload a file to the currently logged in remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)
    :param str local_path: path to the file on the local machine
    :param str remote_path: path to the file on the remote server
    """
    req_url = f"{remote_url}/storage/default{prepend_separator(remote_path)}"
    auth_token = workspace.get_auth_token(remote_url)
    with open(local_path, "rb") as file:
        response = requests.post(
            req_url, files={"file": file}, headers=create_header(auth_token)
        )
        if check_and_print_http_error(response):
            return False
        return True


def download_file(remote_url, remote_path, local_path):
    """
    Download a file from the currently logged in remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000/api/v1)
    :param str remote_path: path to the file on the remote server
    :param str local_path: absolute path to the file on the local machine
    """
    req_url = f"{remote_url}/storage/default{prepend_separator(remote_path)}"
    auth_token = workspace.get_auth_token(remote_url)
    response = requests.get(req_url, headers=create_header(auth_token), stream=True)
    if check_and_print_http_error(response):
        return False
    try:
        with open(local_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    file.write(chunk)
    except Exception as e:
        print(f"Could not download file to {local_path}")
        (print(f"Error: {e}"))
        return False
    return True


def prepend_separator(file_path):
    # add leading slash to relative paths
    if not file_path.startswith("/"):
        file_path = "/" + file_path
    return file_path
