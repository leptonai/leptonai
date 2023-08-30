import requests
import concurrent.futures
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


def uppgrade_workspace_version(workspace_name, version):
    '''
    Input:
        workspace_name: str
        version: str, e.g. '0.8.3'
    '''
    url = mothership_url + "/workspaces" 
    headers = {
        "Authorization": "Bearer {}".format(mothership_key),
    }
    workspace_info = get_workspace_info_from_mothership(workspace_name)
    workspace_info['spec']['git_ref'] = version
    workspace_info['spec']['image_tag'] = version

    response = requests.patch(url, headers=headers, json=workspace_info['spec'])
    return response


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


def get_all_ws_stats():
    ws_total = get_workspaces()
    workspace_ids = [w['spec']['name'] for w in ws_total]
    out = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(get_ws_stat, workspace_id): workspace_id for workspace_id in workspace_ids}
        for future in concurrent.futures.as_completed(future_to_url):
            workspace_id = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (workspace_id, exc))
            else:
                out.append(data)

    result = pd.DataFrame(out, columns=['workspace_id', 'ws_display_name', 'num_of_photons', 'num_of_deployments', 'cpu', 'memory', 'gpu'])
    result = result.sort_values(by=['num_of_photons'], ascending=False)
    return result


def get_ws_stat(workspace_id):
    prefix = 'app' if ENV == 'PROD' else 'cloud'
    base_url = "https://{}.{}.lepton.ai/api/v1/".format(workspace_id, prefix)
    ws_info = get_workspace_info_from_mothership(workspace_id)
    try:
        ws_api_token = ws_info['spec']['api_token']
    except:
        ws_api_token = ''
    ws_display_name = ws_info['spec']['description']
    headers = {
        "Authorization": "Bearer {}".format(ws_api_token),
        "Content-Type": "application/json"
    }   
    # get resouce usage
    url = base_url + "workspace"
    res = requests.get(url, headers=headers).json()
    cpu = round(res['resource_quota']['used']['cpu'], 2)
    memory = round(res['resource_quota']['used']['memory'] / 1024, 2)
    gpu = res['resource_quota']['used']['accelerator_num']
    # get num of photons
    url = base_url + "photons"   
    num_of_photons = len(requests.get(url, headers=headers).json())
    # get num of deployments
    url = base_url + "deployments"
    num_of_deployments = len(requests.get(url, headers=headers).json())
    
    info = [workspace_id, ws_display_name, num_of_photons, num_of_deployments, cpu, memory, gpu]
    return info