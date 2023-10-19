from datetime import datetime, timezone
import os

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError
except ImportError:
    print("boto3 not installed. S3Cache will not work.")
    print("If you want to use S3Cache, install boto3 with `pip install boto3`.")


class S3Cache:
    """
    A simple utility function to cache files from S3 to a local folder.

    S3Cache allows you to access files in an S3 bucket as if they were local files,
    and deals with download and caching of the files for you.

    Example usage:

        ```
        from leptonai.util import S3Cache
        cache = S3Cache(bucket="my-bucket", local_folder="/tmp/my-cache")
        # Optionally, you can also specify AWS credentials:
        # cache = S3Cache(
        #     bucket="my-bucket",
        #     local_folder="/tmp/my-cache",
        #     aws_access_key_id="my-access-key",
        #     aws_secret_access_key="my-secret-key"
        # )
        # Get a file from S3, and download it if it doesn't exist locally
        local_path = cache.get("path/to/file.txt")
        # Sync the whole folder from S3
        cache.rsync("path/to/folder")
        ```
    """

    def __init__(
        self, bucket, local_folder, aws_access_key_id=None, aws_secret_access_key=None
    ):
        """
        Creates a new S3Cache object.

        Args:
            bucket: The name of the S3 bucket to cache.
            local_folder: The local folder to cache the files to.
            aws_access_key_id: The AWS access key ID to use. If not specified, the default credentials will be used.
            aws_secret_access_key: The AWS secret access key to use. If not specified, the default credentials will be used.
        """
        self.local_folder = local_folder
        self.s3_bucket = bucket
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        # Ensure the local folder exists
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

    def get(self, s3_path, check_freshness=False):
        """
        Fetches the content from s3://bucketname/s3_path, if it exists.
        Downloads the file if it does not exist, or it is newer than the local version (if check_freshness is specified).

        Args:
            s3_path: The path to the file in S3.
            check_freshness: If True, check if the local file is fresher than the S3
                version, and only download if it is older. Defaults to False. This saves
                bandwidth, but can cause issues if the S3 file is updated and the local file is not updated.
        """
        local_path = os.path.join(self.local_folder, s3_path)

        if os.path.exists(local_path):
            # If the file is in local cache and no check freshness needed, then
            # directly return the path.
            if not check_freshness:
                return local_path
            # Otherwise, check freshness
            # Fetch the modification time of the local file
            local_file_mtime = datetime.fromtimestamp(
                os.path.getmtime(local_path), timezone.utc
            )
            # Check the modification time of the S3 object
            try:
                s3_obj_metadata = self.s3_client.head_object(
                    Bucket=self.s3_bucket, Key=s3_path
                )
                s3_last_modified = s3_obj_metadata["LastModified"]
                # If the local file is fresher or equally fresh as the S3 version, return the local path
                if local_file_mtime >= s3_last_modified:
                    return local_path
            except self.s3_client.exceptions.NoSuchKey:
                raise FileNotFoundError(f"{s3_path} not found in S3.")
            except (NoCredentialsError, PartialCredentialsError) as e:
                raise e
            except Exception as e:
                raise RuntimeError(f"Error checking {s3_path} in S3: {e}")
        # If we reached this point, we need to download the file from S3
        try:
            local_dir = os.path.dirname(local_path)
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            self.s3_client.download_file(self.s3_bucket, s3_path, local_path)
            return local_path
        except Exception as e:
            raise RuntimeError(f"Error downloading {s3_path} in S3.") from e

    def rsync(self, folder_name):
        """
        Syncs the content of s3://bucketname/folder_name to the local folder.

        Args:
            folder_name: The name of the folder in S3 to sync. To sync the whole bucket, use "".
        """
        # Note: currently, this is not using parallel downloads, so if you
        # are downloading large amounts of small files, this might be slow.
        try:
            # List all files in the specified S3 folder
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket, Prefix=folder_name
            )
            if "Contents" in response:
                for item in response["Contents"]:
                    file_path = item["Key"]
                    if file_path.endswith("/"):
                        # It's a directory. Skip.
                        continue
                    local_path = os.path.join(self.local_folder, file_path)
                    local_dir = os.path.dirname(local_path)
                    if not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                    self.s3_client.download_file(self.s3_bucket, file_path, local_path)
        except Exception as e:
            raise RuntimeError(f"Error syncing {folder_name} from S3.") from e
