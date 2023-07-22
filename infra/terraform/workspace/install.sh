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

if [[ -z $WORKSPACE_NAME ]]; then
  echo "ERROR: Workspace name not specified"
  exit 1
fi

if [[ -z $OIDC_ID ]]; then
  echo "ERROR: OIDC ID not specified"
  exit 1
fi

if [[ -z $IMAGE_TAG ]]; then
  IMAGE_TAG="latest"
fi

if [[ -z $API_TOKEN ]]; then
  API_TOKEN=""
fi

if [[ -z $WEB_ENABLED ]]; then
  WEB_ENABLED="false"
fi

if [[ -z $CREATE_EFS ]]; then
  CREATE_EFS="false"
fi

if [[ $CREATE_EFS == "false" ]]; then
  EFS_MOUNT_TARGETS="null"
  VPC_ID=""
fi

if [[ $CREATE_EFS == "true" ]]; then
  if [[ -z $EFS_MOUNT_TARGETS ]]; then
    echo "ERROR: must set EFS_MOUNT_TARGETS when CREATE_EFS is true"
    exit 1
  fi
  if [[ -z $VPC_ID ]]; then
    echo "ERROR: must set VPC_ID when CREATE_EFS is true"
    exit 1
  fi
fi

if [[ -z $EFS_MOUNT_TARGETS ]]; then
  EFS_MOUNT_TARGETS="{}"
fi

# shellcheck source=/dev/null
source ../lib.sh

if [[ -z $TF_WORKSPACE ]]; then
  export TF_WORKSPACE="ws-$WORKSPACE_NAME-default"
else
  export TF_WORKSPACE
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

echo "Creating Workspace $WORKSPACE_NAME at Cluster $CLUSTER_NAME..."

must_create_workspace "$TF_WORKSPACE" "$TF_API_TOKEN"

if terraform init --upgrade ; then
  echo "SUCCESS: Terraform init completed successfully"
else
  echo "ERROR: Terraform init failed"
  exit 1
fi

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
ENABLE_COPY_LEPTON_CHARTS=${ENABLE_COPY_LEPTON_CHARTS:-false}
if [[ "$ENABLE_COPY_LEPTON_CHARTS" == "true" ]]; then
  # this is not running via mothership, thus requiring manual copy
  echo "copying lepton charts from ../../../charts"
  rm -rf ./charts || true
  cp -r ../../../charts .
else
  echo "skipping copying lepton charts"
fi

# loads additional flags and values for the following "terraform apply" commands
# shellcheck source=/dev/null
source ./variables.sh

export TF_LOG="DEBUG"
export TF_LOG_PATH="tf.install.log"

echo "Applying resources..."
terraform apply "${APPLY_FLAGS[@]}"
apply_output=$(terraform apply "${APPLY_FLAGS[@]}" 2>&1)
if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
  echo "SUCCESS: Terraform apply of all modules completed successfully"
else
  echo "FAILED: Terraform apply of all modules failed"
  exit 1
fi
