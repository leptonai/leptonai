import json
import os
import tempfile

from cryptography.fernet import Fernet
from django.http import HttpResponse
from dotenv import load_dotenv
from google.cloud import storage
from loguru import logger

from .models import BaseModel


def json_response(obj):
    if isinstance(obj, BaseModel):
        data = obj.to_dict()
    elif isinstance(obj, list):
        data = [o.to_dict() for o in obj]
    else:
        raise TypeError("obj must be a Django model or a list of Django models")
    return HttpResponse(json.dumps(data), content_type="application/json")


def _upload_to_gcs(file_obj, bucket, bucket_path):
    if "GCP_SERVICE_ACCOUNT_JSON" not in os.environ:
        load_dotenv(".env.gcp")

    with tempfile.NamedTemporaryFile() as f:
        f.write(
            Fernet(os.environ["GCP_FERNET_KEY"].encode("utf-8")).decrypt(
                os.environ["GCP_SERVICE_ACCOUNT_JSON"].encode("utf-8")
            )
        )
        f.flush()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
        storage_client = storage.Client()
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    bucket_obj = storage_client.get_bucket(bucket)
    blob = bucket_obj.blob(bucket_path)
    blob.upload_from_file(file_obj)
    return blob.public_url


def upload_dataset(file_obj, id_):
    logger.info(f"Uploading {file_obj} to dataset")
    bucket = "tuna-dish"
    bucket_path = f"dataset/{id_}.json"
    _upload_to_gcs(file_obj, bucket, bucket_path)
    return f"gs://{bucket}/{bucket_path}"


def get_output_dir(id_):
    bucket = "tuna-dish"
    bucket_path = f"output/{id_}"
    return f"gs://{bucket}/{bucket_path}"
