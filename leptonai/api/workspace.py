import yaml

from leptonai.config import CACHE_DIR

WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"


def load_workspace_info():
    workspace_info = {"workspaces": {}, "current_workspace": None}
    if WORKSPACE_FILE.exists():
        with open(WORKSPACE_FILE) as f:
            workspace_info = yaml.safe_load(f)
    return workspace_info


def save_workspace(name, url, terraform_dir=None, auth_token=None):
    workspace_info = load_workspace_info()
    workspace_info["workspaces"][name] = {}
    workspace_info["workspaces"][name]["url"] = url
    workspace_info["workspaces"][name]["terraform_dir"] = terraform_dir
    workspace_info["workspaces"][name]["auth_token"] = auth_token

    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def remove_workspace(name):
    workspace_info = load_workspace_info()
    workspace_info["workspaces"].pop(name)
    if workspace_info["current_workspace"] == name:
        workspace_info["current_workspace"] = None
    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def set_current_workspace(name):
    workspace_info = load_workspace_info()
    workspace_info["current_workspace"] = name
    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def get_auth_token(workspace_url):
    #  TODO: Store current auth token in yaml for constant time access
    workspace_info = load_workspace_info()
    for _, vals in workspace_info["workspaces"].items():
        if vals["url"] == workspace_url:
            return vals["auth_token"]
    return None


def get_current_workspace_url():
    workspace_info = load_workspace_info()
    current_workspace = workspace_info["current_workspace"]
    if current_workspace is None:
        return None
    workspaces = workspace_info["workspaces"]
    return workspaces[current_workspace]["url"]


def get_workspace_url(workspace_url=None):
    if workspace_url is not None:
        return workspace_url
    return get_current_workspace_url()
