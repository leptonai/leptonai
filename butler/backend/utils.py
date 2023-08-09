import json
import requests
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Asm
import random
import string
import dotenv
import database
import workspace
import user

dotenv.load_dotenv()

send_grid_api_key = os.environ.get("SEND_GRID_KEY")
ENV = os.environ.get("ENV")
if ENV == "PROD":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_PROD")
    mothership_url = os.environ.get("MOTHERSHIP_URL_PROD")
    cluster_name = os.environ.get("MOTHERSHIP_CLUSTER_NAME_PROD")
elif ENV == "DEV":
    mothership_key = os.environ.get("MOTHERSHIP_KEY_DEV")
    mothership_url = os.environ.get("MOTHERSHIP_URL_DEV")
    cluster_name = os.environ.get("MOTHERSHIP_CLUSTER_NAME_DEV")


def generate_token(length):
    characters = string.ascii_lowercase + string.digits
    while True:
        token = "".join(random.choice(characters) for _ in range(length))
        if token[0].isdigit():
            continue
        else:
            break
    return token


def send_welcome(destination):
    """
    Input:
        detination : a tuple contains two elements, eg:
            ('yuze.bob.ma@gmail.com', 'Yuze Ma')
    """
    # from address we pass to our Mail object, edit with your name
    FROM_EMAIL = "uz@lepton.ai"

    # update to your dynamic template id from the UI
    TEMPLATE_ID = "d-32c4d10c26c34ee5bafb2bb240dd7860"

    TO_EMAILS = [destination]

    message = Mail(from_email=FROM_EMAIL, to_emails=TO_EMAILS)
    # pass custom values for our HTML placeholders
    message.dynamic_template_data = {"user_name": destination[1]}
    message.template_id = TEMPLATE_ID
    asm = Asm(group_id=21845)
    message.asm = asm

    sg = SendGridAPIClient(send_grid_api_key)
    response = sg.send(message)

    return response


def create_workspace_on_cluster(workspace_display_name):
    workspace_name = generate_token(8)
    api_token = generate_token(32)
    description = workspace_display_name

    url = mothership_url + "/workspaces"
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }

    payload = {
        "name": workspace_name,
        "cluster_name": cluster_name,
        "api_token": api_token,
        "enable_web": False,
        "quota_group": "small",
        "description": description,
        "image_tag": "0.7.1",
        "git_ref": "0.7.1",
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response


def insert_workspace_to_db(workspace_name, workspace_display_name):
    workspace_url = (
        "https://"
        + workspace_name
        + "."
        + mothership_url[
            mothership_url.find("mothership")
            + len("mothership "): mothership_url.find("/api")
        ]
    )
    query = "INSERT INTO workspaces (id, display_name, url) VALUES \
        ('{}', '{}', '{}')".format(
        workspace_name, workspace_display_name, workspace_url
    )
    database.execute_sql(query)


def create_workspace(workspace_display_name):
    response = create_workspace_on_cluster(workspace_display_name)
    if response.status_code != 201:
        print(response.content)
        return json.loads(response.content)
    else:
        workspace_info = json.loads(response.content)
    workspace_id = workspace_info["spec"]["name"]
    workspace_display_name = workspace_info["spec"]["description"]
    insert_workspace_to_db(workspace_id, workspace_display_name)
    print("Workspace {} successfully created".format(workspace_display_name))
    print("Workspace ID: {}".format(workspace_id))
    return workspace_info


def list_workspace_users(workspace_id):
    '''
    This function is used to list all users in a workspace.
    '''
    return workspace.get_workspace_users(workspace_id)


def invite_user(email):
    '''
    This function is used to invite a user to the platform by email.
    '''
    result = user.add_user(email)
    if result['enable']:
        send_welcome((email, email))
    return result


def enable_user(email):
    return user.activate_user(email)


def add_user_to_workspace(email, workspace_id, token):
    target_user = user.get_user_by_email(email)
    user_id = target_user["id"]

    ws_users = database.get_workspace_users(workspace_id)
    if user_id in ws_users:
        print("User {} already in workspace {}".format(email, workspace_id))
        return

    max_id = database.get_max_id_for_user_workspace()
    query = "INSERT INTO user_workspace ( id , workspace_id, user_id, token) \
        VALUES ('{}','{}', '{}', '{}')".format(
        max_id + 1, workspace_id, user_id, token
    )
    database.execute_sql(query)
    return "User {} successfully added to \
        workspace {}".format(email, workspace_id)


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
        workspace {}".format(email, workspace_id)
