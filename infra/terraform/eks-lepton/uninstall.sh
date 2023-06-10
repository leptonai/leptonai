#!/bin/bash

CLUSTER_NAME=$1

if [ -z "$CLUSTER_NAME" ]; then
  CLUSTER_NAME=$(terraform output -json | jq -r '.cluster_name.value')
fi

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

export "TF_WORKSPACE"=$CLUSTER_NAME

if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "null" ]; then
  echo "ERROR: Cluster name not specified"
else
  terraform destroy -auto-approve -var="cluster_name=$CLUSTER_NAME"
fi
