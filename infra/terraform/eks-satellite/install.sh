#!/bin/bash

set -xe

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

if [[ -z $SATELLITE_NAME ]]; then
  echo "ERROR: Satellite name not specified"
  exit 1
fi

echo "Creating satellite $SATELLITE_NAME resources for the cluster $CLUSTER_NAME..."

# shellcheck source=/dev/null
source ../lib.sh

# NOTE: we want to enforce terraform workspace
if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi
if [[ -z $TF_WORKSPACE ]]; then
  export TF_WORKSPACE="satellite-$CLUSTER_NAME-$SATELLITE_NAME"
else
  export TF_WORKSPACE
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

echo "creating terraform workspace ${TF_WORKSPACE}"
must_create_workspace "$TF_WORKSPACE" "$TF_API_TOKEN"

terraform init --upgrade
echo "SUCCESS: Terraform init completed successfully"

# loads additional flags and values for the following "terraform apply" commands
# shellcheck source=/dev/null
source ./variables.sh

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.install.log"

terraform apply "${APPLY_FLAGS[@]}"
echo "SUCCESS: Terraform apply of all modules completed successfully"
