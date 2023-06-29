#! /usr/bin/env python3

import sys, json, random, string, time
import requests


def create_cluster(cluster_name, auth_token, git_ref):
    url = "https://mothership.cloud.lepton.ai/api/v1/clusters"
    data = {
        "name": cluster_name,
        "git_ref": git_ref,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + auth_token,
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    if response.status_code >= 200 and response.status_code < 300:
        print(f"Cluster {cluster_name} creation request sent successfully")
        return True
    print(f"Cluster {cluster_name} creation request sent failed")
    return False


def delete_cluster(cluster_name, auth_token):
    url = f"https://mothership.cloud.lepton.ai/api/v1/clusters/{cluster_name}"
    headers = {"Authorization": "Bearer " + auth_token}
    response = requests.delete(url, headers=headers)
    if response.status_code >= 200 and response.status_code < 300:
        print(f"Cluster {cluster_name} deletion request sent successfully")
        return True
    print(f"Cluster {cluster_name} deletion request sent failed")
    return False


def check_ready(cluster_name, auth_token):
    url = f"https://mothership.cloud.lepton.ai/api/v1/clusters/{cluster_name}"
    headers = {"Authorization": "Bearer " + auth_token}
    response = requests.get(url, headers=headers)
    if response.status_code >= 200 and response.status_code < 300:
        resp = json.loads(response.text)
        if (
            "status" in resp
            and "state" in resp["status"]
            and resp["status"]["state"] == "ready"
        ):
            print(f"Cluster {cluster_name} is ready")
            return True
    print(f"Cluster {cluster_name} is not ready")
    return False


def check_deleted(cluster_name, auth_token):
    url = f"https://mothership.cloud.lepton.ai/api/v1/clusters/{cluster_name}"
    headers = {"Authorization": "Bearer " + auth_token}
    response = requests.get(url, headers=headers)
    if response.status_code >= 500:
        if "failed to get cluster" in response.text:
            print(f"Cluster {cluster_name} deletion finished")
            return True
    print(f"Cluster {cluster_name} deletion not finished")
    return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 test_cluster_creation.py <auth_token> <git_ref>")
        sys.exit(1)
    auth_token = sys.argv[1]
    git_ref = sys.argv[2]
    cluster_name = "ci" + "".join(
        random.choice(string.ascii_lowercase) for _ in range(8)
    )
    print(f"Testing cluster name: {cluster_name} with git ref: {git_ref}")

    # do cluster creation
    if not create_cluster(cluster_name, auth_token, git_ref):
        delete_cluster(cluster_name, auth_token)
        sys.exit(1)
    # if it doesn't finish creation in 2 hours, we fail the test, because mothership
    # has a timeout of 2 hours for cluster creation
    start_time = time.time()
    print("Cluster creation start time: " + time.ctime(start_time))
    while True:
        time.sleep(60)
        if check_ready(cluster_name, auth_token):
            break
        end_time = time.time()
        if end_time - start_time > 7200 + 60:  # 2 hours + a little buffer
            print("Cluster creation timeout" + time.ctime(end_time))
            delete_cluster(cluster_name, auth_token)
            sys.exit(1)
    print("Cluster creation end time: " + time.ctime(time.time()))

    # do cluster deletion
    if not delete_cluster(cluster_name, auth_token):
        sys.exit(1)
    # if it doesn't finish deletion in 2 hours, we fail the test, because mothership
    # has a timeout of 2 hours for cluster deletion
    start_time = time.time()
    print("Cluster deletion start time: " + time.ctime(start_time))
    while True:
        time.sleep(60)
        if check_deleted(cluster_name, auth_token):
            break
        end_time = time.time()
        print("Cluster deletion timeout" + time.ctime(end_time))
        if end_time - start_time > 7200:
            sys.exit(1)
    print("Cluster deletion end time: " + time.ctime(time.time()))
