import json
import requests
import os
import random
import string
import dotenv
import database
import workspace
import user
import mail_utils

dotenv.load_dotenv()

SHARED = "shared"
DEDICATED = "dedicated"

send_grid_api_key = os.environ.get("SEND_GRID_KEY")
lepton_api_secret = os.environ.get("LEPTON_API_SECRET")
ENV = os.environ.get("ENV")
if ENV == "PROD":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_PROD")
    mothership_url = os.environ.get("MOTHERSHIP_URL_PROD")
    cluster_name = os.environ.get("MOTHERSHIP_CLUSTER_NAME_PROD")
    cluster_alias_in_hostname = os.environ.get("SHARED_LB_URL_CLUSTER_ALIAS_PROD")
    shared_lb_url_main_domain = os.environ.get("SHARED_LB_URL_MAIN_DOMAIN_PROD")
elif ENV == "DEV":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_DEV")
    mothership_url = os.environ.get("MOTHERSHIP_URL_DEV")
    cluster_name = os.environ.get("MOTHERSHIP_CLUSTER_NAME_DEV")
    cluster_alias_in_hostname = os.environ.get("SHARED_LB_URL_CLUSTER_ALIAS_DEV")
    shared_lb_url_main_domain = os.environ.get("SHARED_LB_URL_MAIN_DOMAIN_DEV")


def generate_token(length):
    characters = string.ascii_lowercase + string.digits
    while True:
        token = "".join(random.choice(characters) for _ in range(length))
        if token[0].isdigit():
            continue
        else:
            break
    return token


def create_workspace_on_cluster(workspace_display_name, lb_type="shared"):
    workspace_name = generate_token(8)
    api_token = generate_token(32)
    description = workspace_display_name

    url = mothership_url + "/workspaces"
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }

    version = "0.9.1"
    payload = {
        "name": workspace_name,
        "cluster_name": cluster_name,
        "api_token": api_token,
        "enable_web": False,
        "quota_group": "small",
        "description": description,
        "tier": "basic",  # Could be basic, standard, enterprise
        "image_tag": version,
        "git_ref": version,
        "lb_type": lb_type,
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response


def create_workspace_url(workspace_name, lb_type=SHARED) -> str:
    if lb_type not in [SHARED, DEDICATED]:
        print(
            f"Load balancer type should be either {SHARED} or {DEDICATED}, but got {lb_type}"
        )
        exit(1)
    else:
        print(f"Using loadbalancer type {lb_type}")

    if lb_type == SHARED and (
        cluster_alias_in_hostname == "" or shared_lb_url_main_domain == ""
    ):
        print(
            f"Bad input: cluster_alias_in_hostname {cluster_alias_in_hostname} and shared_lb_url_main_domain {shared_lb_url_main_domain} should both be non-empty"
        )
        exit(1)

    workspace_url = (
        "https://" + workspace_name
        + "."
        + cluster_alias_in_hostname
        + "."
        + shared_lb_url_main_domain
    )
    if lb_type == DEDICATED:
        workspace_url = (
            "https://"
            + workspace_name
            + "."
            + mothership_url[
                mothership_url.find("mothership")
                + len("mothership "): mothership_url.find("/api")
            ]
        )
    return workspace_url


def insert_workspace_to_db(workspace_name, workspace_display_name, lb_type=SHARED):
    workspace_url = create_workspace_url(workspace_name, lb_type=lb_type)
    query = "INSERT INTO workspaces (id, display_name, url, tier, chargeable) VALUES \
        ('{}', '{}', '{}', 'Basic', 'FALSE')".format(
        workspace_name, workspace_display_name, workspace_url
    )
    database.execute_sql(query)


def create_workspace(workspace_display_name, lb_type=SHARED):
    response = create_workspace_on_cluster(workspace_display_name, lb_type=lb_type)
    if response.status_code != 201:
        print(response.content)
        return json.loads(response.content)
    else:
        workspace_info = json.loads(response.content)
    workspace_id = workspace_info["spec"]["name"]
    workspace_display_name = workspace_info["spec"]["description"]
    insert_workspace_to_db(workspace_id, workspace_display_name, lb_type=lb_type)
    print("Workspace {} successfully created".format(workspace_display_name))
    print("Workspace ID: {}".format(workspace_id))
    return workspace_info


def list_workspace_users(workspace_id):
    """
    This function is used to list all users in a workspace.
    """
    return workspace.get_workspace_users(workspace_id)


def invite_user(email):
    """
    This function is used to invite a user to the platform by email.
    """
    result = user.add_user(email)
    if result["enable"]:
        mail_utils.send_welcome((email, email))
    return result


def enable_user(email):
    return user.activate_user(email)


def add_user_to_workspace(email, workspace_id):
    target_user = user.get_user_by_email(email)
    user_id = target_user["id"]

    ws_users = database.get_workspace_users(workspace_id)
    if user_id in ws_users:
        print("User {} already in workspace {}".format(email, workspace_id))
        return

    token = workspace.get_workspace_info_from_mothership(workspace_id)["spec"][
        "api_token"
    ]

    max_id = database.get_max_id_for_user_workspace()
    query = "INSERT INTO user_workspace ( id , workspace_id, user_id, token) \
        VALUES ('{}','{}', '{}', '{}')".format(
        max_id + 1, workspace_id, user_id, token
    )
    database.execute_sql(query)
    return "User {} successfully added to \
        workspace {}".format(
        email, workspace_id
    )


def remove_user_from_workspace(email, workspace_id):
    target_user = user.get_user_by_email(email)
    user_id = target_user["id"]

    ws_users = database.get_workspace_users(workspace_id)
    if user_id not in ws_users:
        print("User {} not in workspace {}".format(email, workspace_id))
        return

    query = "DELETE FROM user_workspace WHERE workspace_id = '{}' \
        AND user_id = '{}'".format(
        workspace_id, user_id
    )
    database.execute_sql(query)
    return "User {} successfully removed from \
        workspace {}".format(
        email, workspace_id
    )


def set_payment(workspace_id):
    return workspace.reset_workspace_subscription(workspace_id)


def grant_coupon(workspace_id, amount):
    return workspace.grant_coupon(workspace_id, amount)
