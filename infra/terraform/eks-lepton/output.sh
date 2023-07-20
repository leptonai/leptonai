#!/bin/bash

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

export TF_WORKSPACE="cl-$CLUSTER_NAME"
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

terraform output -json | jq 'with_entries(.value = .value.value)'
