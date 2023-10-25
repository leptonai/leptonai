from fastapi import FastAPI, UploadFile, HTTPException, File, Header
import glob
import hashlib
import os
import re
from pathlib import Path
from typing import Union
from urllib.parse import quote

from leptonai import Client, Remote, Photon


class ChunkedFileServer(Photon):
    """
    A Photon class to deal with chunked file uploads.
    """

    @Photon.handler(mount=True)
    def fastapi(self):
        app = FastAPI()
        UPLOAD_ROOT = os.environ.get("LEPTON_LFS_UPLOAD_ROOT", "/tmp")  # Local directory to store uploaded files
        STATUS_FILE_EXTENSION = ".lepton_partial_upload_status"

        @app.post("/upload/")
        def upload_file(path: str, file: UploadFile = File(), content_range: str = Header(None)):
            if not content_range:
                raise HTTPException(status_code=400, detail="Content-Range header required")
            
            resolved_path = Path(UPLOAD_ROOT) / path
            resolved_path_with_status = resolved_path.with_suffix(resolved_path.suffix + STATUS_FILE_EXTENSION)

            try:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid path specified")
        
            # Parse Content-Range header
            range_type, range_info = content_range.split()
            if not range_type == "bytes":
                raise HTTPException(status_code=400, detail="Invalid range type specified")
            
            start, end, total = map(int, re.findall(r"\d+", range_info))

            if not os.path.exists(resolved_path):
                with open(resolved_path, "wb") as f:
                    f.truncate(total)
            elif os.path.getsize(resolved_path) != total:
                raise HTTPException(status_code=400, detail="Invalid range specified. File size mismatch.")

            if not os.path.exists(resolved_path_with_status):
                last_start = 0
            else:
                with open(resolved_path_with_status, "r") as f:
                    last_start = int(f.read())

            if start != last_start:
                raise HTTPException(status_code=400, detail=f"Invalid range specified. Last uploaded byte: {last_start}.")
            
            # Write the chunk to the file
            with open(resolved_path, "r+b") as f:
                f.seek(start)
                f.write(file.file.read())

            with open(resolved_path_with_status, "w") as f:
                f.write(str(end))

            if end == total:
                return {"status": "ok", "total": total}
            else:
                return {"status": "partial", "total": total, "next_byte": end}
        
        @app.post("/delete/")
        def delete_file(path: str):
            resolved_path = Path(UPLOAD_ROOT) / path
            resolved_path_with_status = resolved_path.with_suffix(resolved_path.suffix + STATUS_FILE_EXTENSION)
            if not os.path.exists(resolved_path):
                raise HTTPException(status_code=404, detail="File not found")
            else:
                os.remove(resolved_path)
                if os.path.exists(resolved_path_with_status):
                    os.remove(resolved_path_with_status)
                return {"status": "ok"}

        @app.get("/upload_status/")
        def upload_status(path: str):
            resolved_path = (Path(UPLOAD_ROOT) / path)
            resolved_path_with_status = resolved_path.with_suffix(resolved_path.suffix + STATUS_FILE_EXTENSION)
            if not os.path.exists(resolved_path):
                return {"status": "not found"}
            else:
                total = os.path.getsize(resolved_path)
                if not os.path.exists(resolved_path_with_status):
                    return {"status": "partial", "total": total, "uploaded_bytes": 0}
                else:
                    with open(resolved_path_with_status, "r") as f:
                        uploaded_bytes = int(f.read())
                        if uploaded_bytes == total:
                            return {"status": "ok", "total": total}
                        else:
                            return {"status": "partial", "total": total, "uploaded_bytes": uploaded_bytes}
                        
        @app.get("/md5sum/")
        def md5sum(path: str):
            resolved_path = (Path(UPLOAD_ROOT) / path)
            if not os.path.exists(resolved_path):
                raise HTTPException(status_code=404, detail="File not found")
            else:
                md5 = hashlib.md5()
                with open(resolved_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(1024*1024), b''):
                        md5.update(chunk)
                return md5.hexdigest()
                        
        return app
                        

class Uploader(object):
    """
    A class to upload files to the chunked file server.
    """
    def __init__(self, client_or_remote: Union[Client, Remote], chunk_size: int = 1024 * 1024 * 10 ):
        """
        Initializes the uploader.

        Inputs:
        - client: a leptonai.Client object
        - chunk_size: the chunk size in bytes. Defaults to 10MB.
        """
        if isinstance(client_or_remote, Remote):
            self.client = client_or_remote.client
        elif isinstance(client_or_remote, Client):
            self.client = client_or_remote
        else:
            raise TypeError("client_or_remote must be a leptonai.Client or leptonai.Remote object")
        self.chunk_size = chunk_size

    def get_upload_status(self, path: str):
        """
        Gets the upload status of a file. Returns a dictionary with the following keys:
        - status: one of "ok", "partial", "not found"
        - total: the total size of the file in bytes (if status is "ok" or "partial")
        - uploaded_bytes: the number of bytes uploaded so far (if status is "partial")
        """
        response = self.client._get("/fastapi/upload_status/", params={"path": path})
        return response.json()
    
    def md5sum(self, path: str):
        """
        Gets the md5sum of a file. Returns a string.
        """
        response = self.client._get("/fastapi/md5sum/", params={"path": path})
        return response.json()
    
    def upload_file(self, local_path: str, path: str, max_retry: int = 10):
        """
        Uploads a file to the chunked file server. path should be a remote file name, and local_path
        should be a local file name.

        If the file already exists, it will be resumed from the last uploaded byte.
        """
        status = self.get_upload_status(path)

        if status["status"] == "ok":
            print("File already uploaded.")
            return

        if status["status"] == "partial":
            uploaded_bytes = status["uploaded_bytes"]
        else:
            uploaded_bytes = 0

        local_size = os.path.getsize(local_path)
        with open(local_path, "rb") as f:
            f.seek(uploaded_bytes)
            start_byte = uploaded_bytes
            encoded_path = quote(path)
            remaining_retries = max_retry
            while True:
                chunk = f.read(self.chunk_size)
                end_byte = start_byte + len(chunk)
                headers = {
                    "Content-Range": f"bytes {start_byte}-{end_byte}/{local_size}"
                }

                try:
                    response = self.client._post(
                        f"/fastapi/upload/?path={encoded_path}",
                        headers=headers,
                        files={"file": (path.split('/')[-1], chunk)})
                    response.raise_for_status()
                except Exception as e:
                    if remaining_retries > 0:
                        print(f"An error occurred: {e}.\n"
                              " Retrying... ({remaining_retries} retries remaining)")
                        remaining_retries -= 1
                        continue
                    else:
                        print(f"An error occurred: {e}. Please retry the upload.")
                        raise e

                response = response.json()   
                if response["status"] == "ok":
                    print("File upload complete.")
                    return
                elif response["status"] == "partial":
                    print(f"Uploaded up to byte {response['next_byte']}. continuing...")
                    start_byte = response["next_byte"]
                else:
                    raise RuntimeError("A programming error occurred.")
                
    def upload_folder(self, path: str, local_path: str, overwrite: bool = False):
        """
        Uploads a folder to the chunked file server. path should be a remote folder name, and local_path
        should be a local folder name. Any file like `local_path/foo/bar.txt` will be uploaded to
        `path/foo/bar.txt`.

        If overwrite is True, any existing files will be overwritten. Otherwise, they will be skipped.
        """
        # first, find all files under local_path.
        files = [f for f in glob.glob(f"{local_path}/**/*", recursive=True)
                 if os.path.isfile(f)]
        for local_filename in files:
            # Get the relative path of the file
            relative_path = os.path.relpath(local_filename, local_path)
            remote_filename = os.path.join(path, relative_path)
            # check if the file exists on the server
            status = self.get_upload_status(remote_filename)
            if status["status"] == "ok":
                # TODO: check if they are the same files with md5sum
                is_different = status["total"] != os.path.getsize(local_filename)
                if is_different:
                    if overwrite:
                        print(f"Overwriting {remote_filename}")
                        self.upload_file(local_filename, remote_filename)
                    else:
                        print("Skipping {remote_filename} (already exists but different file)")
                else:
                    print(f"Skipping {remote_filename} (already exists, same file)")
            elif status["status"] == "partial":
                print(f"Resuming upload of {remote_filename}")
                self.upload_file(local_filename, remote_filename)
            else:
                print(f"Uploading {remote_filename}")
                self.upload_file(local_filename, remote_filename)