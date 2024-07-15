import os

from typing import Union, List, Dict

from leptonai.api.v1.api_resource import APIResourse
from leptonai.api.v1.types.deployment import (
    DEFAULT_STORAGE_VOLUME_NAME,
)
from leptonai.api.v1.types.storage import FileSystem, DirInfo


def _prepend_separator(file_path):
    """
    Utility function to add leading slash to relative paths if needed
    """
    return file_path if file_path.startswith("/") else "/" + file_path


class StorageAPI(APIResourse):
    def get_file_type(self, file_path: str) -> Union[str, None]:
        """
        Check if the contents at file_path stored on the remote server are a file or a directory.

        :param str file_path: path to the file or directory on the remote server

        Returns "file" or "dir" if the file exists, None otherwise.
        """
        # json output of get_dir does not include trailing separators
        file_path = file_path.rstrip(os.sep)
        file_path = _prepend_separator(file_path)
        parent_dir = (
            "/" if os.path.dirname(file_path) == "" else os.path.dirname(file_path)
        )

        parent_contents = self.get_dir(parent_dir)

        base = os.path.basename(file_path)
        for dir_info in parent_contents:
            if dir_info.name == base:
                return dir_info.type
        return None

    def list_storage(self) -> List[FileSystem]:
        response = self._get("/storage")
        return self.ensure_list(response, FileSystem)

    def get_file(self, remote_path: str, local_path: str) -> Dict[str, str]:
        response = self._get(
            f"/storage/{DEFAULT_STORAGE_VOLUME_NAME}{_prepend_separator(remote_path)}",
            stream=True,
        )
        self.ensure_ok(response)

        try:
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        file.write(chunk)
        except Exception as e:
            return self._print_programming_error(response, e)

        return {"name": local_path}

    def get_dir(self, remote_path: str) -> List[DirInfo]:
        response = self._get(
            f"/storage/{DEFAULT_STORAGE_VOLUME_NAME}{_prepend_separator(remote_path)}",
        )
        return self.ensure_list(response, DirInfo)

    def create_file(self, local_path: str, remote_path: str) -> bool:
        with open(local_path, "rb") as file:
            response = self._post(
                f"/storage/{DEFAULT_STORAGE_VOLUME_NAME}{_prepend_separator(remote_path)}",
                files={"file": file},
            )
            return self.ensure_ok(response)

    def create_dir(self, additional_path: str) -> bool:
        response = self._put(
            f"/storage/{DEFAULT_STORAGE_VOLUME_NAME}{_prepend_separator(additional_path)}"
        )
        return self.ensure_ok(response)

    def delete_file_or_dir(self, additional_path: str) -> bool:
        response = self._delete(
            f"/storage/{DEFAULT_STORAGE_VOLUME_NAME}{_prepend_separator(additional_path)}"
        )
        return self.ensure_ok(response)

    def check_exists(self, additional_path: str) -> bool:
        response = self._head(
            f"/storage/{DEFAULT_STORAGE_VOLUME_NAME}{_prepend_separator(additional_path)}"
        )

        return response.status_code == 200

    def total_file_system_usage_bytes(self) -> FileSystem:
        response = self._get("/storage/du")
        return self.ensure_type(response, FileSystem)
