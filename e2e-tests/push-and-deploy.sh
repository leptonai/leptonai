#! /bin/sh

set -e
set -x

NAMESPACE=$1
if [ -z "$NAMESPACE" ]; then
    exit 1
fi

PHOTON_NAME=gpt2

REMOTE=$(kubectl -n "$NAMESPACE" get ingress | grep lepton-ingress | head -n1 | awk '{print $4}')
if [ -z "$REMOTE" ]; then
    exit 1
fi

until host "$REMOTE" > /dev/null ;do sleep 1; done
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
