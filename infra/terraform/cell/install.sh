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

if [[ -z $CREATE_EFS ]]; then
  $CREATE_EFS=false
fi

# shellcheck source=/dev/null
source ../lib.sh

export TF_WORKSPACE=$CLUSTER_NAME-$CELL_NAME

echo "Creating Cell $CELL_NAME at Cluster $CLUSTER_NAME..."

must_create_workspace "$TF_WORKSPACE" "$TF_API_TOKEN"

# initialize Terraform
terraform init --upgrade

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
if [[ -z $COPY_LEPTON_CHARTS ]]; then
  echo "skipping copying lepton charts"
else
  # this is not running via mothership, thus requiring manual copy
  echo "copying lepton charts from ../../../charts/lepton"
  rm -rf ./lepton || true
  cp -r ../../../charts/lepton ./lepton
fi

echo "Applying resources..."
terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" \
  -var="namespace=$CELL_NAME" -var="cell_name=$CELL_NAME" \
  -var="oidc_id=$OIDC_ID" -var="api_token=$API_TOKEN" \
  -var "image_tag_web=$IMAGE_TAG" \
  -var "image_tag_api_server=$IMAGE_TAG" \
  -var "image_tag_deployment_operator=$IMAGE_TAG" \
  -var "create_efs=$CREATE_EFS" \
  -var "efs_mount_targets=$EFS_MOUNT_TARGETS"
apply_output=$(terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" \
  -var="namespace=$CELL_NAME" -var="cell_name=$CELL_NAME" \
  -var="oidc_id=$OIDC_ID" -var="api_token=$API_TOKEN" \
  -var "image_tag_web=$IMAGE_TAG" \
  -var "image_tag_api_server=$IMAGE_TAG" \
  -var "image_tag_deployment_operator=$IMAGE_TAG" \
  -var "create_efs=$CREATE_EFS" \
  -var "efs_mount_targets=$EFS_MOUNT_TARGETS" 2>&1)
if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
  echo "SUCCESS: Terraform apply of all modules completed successfully"
else
  echo "FAILED: Terraform apply of all modules failed"
  exit 1
fi
