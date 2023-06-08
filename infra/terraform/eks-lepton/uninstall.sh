#!/bin/bash

CLUSTER_NAME=$1

if [ -z "$CLUSTER_NAME" ]; then
  CLUSTER_NAME=$(terraform output -json | jq -r '.cluster_name.value')
fi

if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "null" ]; then
  terraform destroy -auto-approve
else
  terraform destroy -auto-approve -var="cluster_name=$CLUSTER_NAME"
fi
