#!/bin/bash

set -xe

# List of Terraform modules/resources to destroy in sequence (reverse order of apply)
# need to delete existing kubernetes resources to avoid dependency conflicts
#
targets=(
  "module.eks"
  "module.vpc"
)

if [ -z "$CLUSTER_NAME" ]; then
  CLUSTER_NAME=$(terraform output -json | jq -r '.cluster_name.value')
fi

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

export TF_WORKSPACE="mo-$CLUSTER_NAME"
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

DEPLOYMENT_ENVIRONMENT=${DEPLOYMENT_ENVIRONMENT:-DEV}
REGION=${REGION:-"us-east-1"}
for target in "${targets[@]}"
do
  terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" -target="$target"
  echo "SUCCESS: Terraform destroy ${target} completed successfully"
done

terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME"
echo "SUCCESS: Terraform destroy completed successfully"
