#!/bin/bash

set -xe

# NOTE: we want to enforce terraform workspace
if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

terraform init --upgrade

# loads additional flags and values for the following "terraform apply" commands
# shellcheck source=/dev/null
source ./variables.sh

ARGS=("apply" "-destroy" "$APPLY_FLAGS")
# shellcheck disable=SC2068
terraform ${ARGS[@]}

echo "DESTORY SUCCESS"
