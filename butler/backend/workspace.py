import json
import requests
import pandas as pd
import psycopg2

import os

import dotenv
dotenv.load_dotenv()

ENV = os.environ.get("ENV")
if ENV == "PROD":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_PROD")
    mothership_url = os.environ.get("MOTHERSHIP_URL_PROD")
    cluster_name = os.environ.get("MOTHERSHIP_CLUSTER_NAME_PROD")
elif ENV == "DEV": 
    mothership_key = os.environ.get("MOTHERSHIP_KEY_DEV")
    mothership_url = os.environ.get("MOTHERSHIP_URL_DEV")
    cluster_name = os.environ.get("MOTHERSHIP_CLUSTER_NAME_DEV")

import random
import string

import pprint

def get_workspaces():
    url = mothership_url + '/workspaces'
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }

    response = requests.get(url, headers=headers)

    return response.json()


def get_workspace_info_from_mothership(workspace_name):
    url = mothership_url + '/workspaces/' + workspace_name
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }

    response = requests.get(url, headers=headers)
    return response.json()