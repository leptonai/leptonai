#!/bin/bash

set -xe

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

if [[ -z $CELL_NAME ]]; then
  echo "ERROR: Cell name not specified"
  exit 1
fi

export TF_WORKSPACE=$CLUSTER_NAME-$CELL_NAME
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

# initialize Terraform
terraform init --upgrade

# refresh once
terraform refresh -var="cluster_name=$CLUSTER_NAME" -var="namespace=$CELL_NAME" -var="cell_name=$CELL_NAME"

echo "Deleting resources..."
terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="namespace=$CELL_NAME" -var="cell_name=$CELL_NAME"
