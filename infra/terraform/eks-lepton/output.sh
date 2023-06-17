#!/bin/bash

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

export TF_WORKSPACE=$CLUSTER_NAME

terraform output -json | jq 'with_entries(.value = .value.value)'
