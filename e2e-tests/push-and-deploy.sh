#! /bin/sh

set -e
set -x

NAMESPACE=$1
if [ -z "$NAMESPACE" ]; then
    exit 1
fi

PHOTON_NAME=gpt2

REMOTE=
# try getting the remote address for 1 minute
for i in $(seq 1 60); do
    REMOTE=$(kubectl -n "$NAMESPACE" get ingress lepton-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    if [ -n "$REMOTE" ]; then
        break
    fi
    sleep 1
done
if [ -z "$REMOTE" ]; then
    exit 1
fi

# try getting the IP of the remote address for 10 minutes
for i in $(seq 1 600); do
    if host "$REMOTE" > /dev/null; then
        break
    fi
    sleep 1
done
if ! host "$REMOTE" > /dev/null; then
    exit 1
fi

REMOTE=http://$REMOTE/api/v1

lepton photon create -n $PHOTON_NAME -m hf:gpt2
lepton photon push -n $PHOTON_NAME -r "$REMOTE"
HASH=$(lepton photon list -r "$REMOTE" | grep $PHOTON_NAME | head -n1 | awk '{print $6}')
if [ -z "$HASH" ]; then
    exit 1
fi

DEPLOYMENT_ID=$(curl -s -X POST -d '{
    "name": "'$NAMESPACE'",
    "photon_id": "'$HASH'",
    "resource_requirement": {
        "cpu": 1,
        "memory": 2048,
        "min_replicas": 1,
        "accelerator_type": "",
        "accelerator_num": 0
    }
}' "$REMOTE"/deployments | jq -r '.id')

if [ -z "$DEPLOYMENT_ID" ]; then
    exit 1
fi
echo "$DEPLOYMENT_ID"

# TODO: continue checking whether the deployment works etc
