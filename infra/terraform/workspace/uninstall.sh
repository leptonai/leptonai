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

export TF_WORKSPACE=$CLUSTER_NAME-$WORKSPACE_NAME
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

# initialize Terraform
terraform init --upgrade

# refresh once
terraform refresh -var="cluster_name=$CLUSTER_NAME" -var="namespace=$WORKSPACE_NAME" -var="workspace_name=$WORKSPACE_NAME" \
  -var="create_efs=$CREATE_EFS" \
  -var="vpc_id=$VPC_ID" \
  -var="efs_mount_targets=$EFS_MOUNT_TARGETS"

echo "Deleting resources..."
terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="namespace=$WORKSPACE_NAME" -var="workspace_name=$WORKSPACE_NAME" \
  -var="create_efs=$CREATE_EFS" \
  -var="vpc_id=$VPC_ID" \
  -var="efs_mount_targets=$EFS_MOUNT_TARGETS"
