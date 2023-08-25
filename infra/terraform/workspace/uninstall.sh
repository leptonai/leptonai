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

if [[ -z $TF_WORKSPACE ]]; then
  export TF_WORKSPACE="ws-$WORKSPACE_NAME-default"
else
  export TF_WORKSPACE
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
ENABLE_COPY_LEPTON_CHARTS=${ENABLE_COPY_LEPTON_CHARTS:-false}
if [[ "$ENABLE_COPY_LEPTON_CHARTS" == "true" ]]; then
  # this is not running via mothership, thus requiring manual copy
  echo "copying lepton workspace charts from ../../../charts"
  rm -rf ./charts && mkdir -p ./charts
  cp -r ../../../charts/workspace ./charts/
else
  echo "skipping copying lepton workspace charts"
fi

terraform init --upgrade
echo "SUCCESS: Terraform init completed successfully"

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.uninstall.log"

terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="region=$REGION" -var="namespace=$WORKSPACE_NAME" -var="workspace_name=$WORKSPACE_NAME" \
  -var="create_efs=$CREATE_EFS" \
  -var="vpc_id=$VPC_ID" \
  -var="efs_mount_targets=$EFS_MOUNT_TARGETS"
echo "SUCCESS: Terraform destroy completed successfully"
