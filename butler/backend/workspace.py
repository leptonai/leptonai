import requests
import os
import dotenv
import database
import json
import pandas as pd

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


def get_workspaces():
    url = mothership_url + "/workspaces"
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)

    return response.json()


def get_workspace_info_from_mothership(workspace_name):
    url = mothership_url + "/workspaces/" + workspace_name
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }

    response = requests.get(url, headers=headers)
    return response.json()


def get_workspace_status(workspace_name: str) -> dict:
    url = mothership_url + "/workspaces/{}".format(workspace_name)
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }
    response = requests.get(url, headers=headers)
    return response.json()


def get_workspace_info(workspace_name: str) -> dict:
    db_connection = database.get_supabase_connection().cursor()
    db_connection.execute(
        "SELECT * FROM workspaces WHERE display_name = '{}'"
        .format(workspace_name)
    )

    rows = db_connection.fetchall()
    res = []

    for row in rows:
        res.append(json.dumps(row))

    return res


def get_workspace_users(workspace_name: str):
    db_connection = database.get_supabase_connection()
    query = '''
    SELECT u.email
    FROM users u
    JOIN user_workspace uw ON u.id = uw.user_id
    WHERE uw.workspace_id = '{}'
    '''.format(workspace_name)
    df = pd.read_sql(query, db_connection)
    db_connection.close()
    return df
