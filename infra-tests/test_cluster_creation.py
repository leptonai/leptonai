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
    print(f"Cluster {cluster_name} creation request sent failed: {response.status_code}")
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


def check_state(cluster_name, auth_token):
    url = f"https://mothership.cloud.lepton.ai/api/v1/clusters/{cluster_name}"
    headers = {"Authorization": "Bearer " + auth_token}
    response = requests.get(url, headers=headers)
    if response.status_code >= 200 and response.status_code < 300:
        resp = json.loads(response.text)
        if "status" in resp and "state" in resp["status"]:
            return resp["status"]["state"]
    if response.status_code >= 500:
        if "failed to get cluster" in response.text:
            return "deleted"
    return "unknown"


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 test_cluster_creation.py <cluster_name> <auth_token> <git_ref> <create/delete>")
        sys.exit(1)
    cluster_name = "ci" + sys.argv[1]
    auth_token = sys.argv[2]
    git_ref = sys.argv[3]
    action = sys.argv[4]
    print(f"Testing {action} cluster. Name: {cluster_name} with git ref: {git_ref}")

    if action == "create":
        if not create_cluster(cluster_name, auth_token, git_ref):
            time.sleep(60)
            sys.exit(1)
        print("Cluster creation start time: " + time.ctime(time.time()))
        while True:
            time.sleep(60)
            state = check_state(cluster_name, auth_token)
            print("Cluster state: " + state + " at " + time.ctime(time.time()))
            if state == "ready":
                break
            if state == "failed":
                print("Cluster creation failed: " + time.ctime(time.now()))
                sys.exit(1)
        print("Cluster creation end time: " + time.ctime(time.time()))

    if action == "delete":
        if not delete_cluster(cluster_name, auth_token):
            sys.exit(1)
        print("Cluster deletion start time: " + time.ctime(time.time()))
        while True:
            time.sleep(60)
            state = check_state(cluster_name, auth_token)
            print("Cluster state: " + state + " at " + time.ctime(time.time()))
            if state == "deleted":
                break
            if state == "failed":
                print("Cluster deletion failed: " + time.ctime(time.now()))
                sys.exit(1)
        print("Cluster deletion end time: " + time.ctime(time.time()))
