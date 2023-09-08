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

echo "Deleting satellite $SATELLITE_NAME resources for the cluster $CLUSTER_NAME..."

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

if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "null" ]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

terraform init --upgrade
echo "SUCCESS: Terraform init completed successfully"

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.uninstall.log"

DEPLOYMENT_ENVIRONMENT=${DEPLOYMENT_ENVIRONMENT:-TEST}
REGION=${REGION:-"us-east-1"}

terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" \
  -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" -var="satellite_name=$SATELLITE_NAME"
echo "SUCCESS: Terraform destroy completed successfully"
