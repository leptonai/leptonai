#!/bin/bash

set -xue

# List of Terraform modules/resources to destroy in sequence (reverse order of apply)
# need to delete existing kubernetes resources to avoid dependency conflicts
#
targets=(
  "module.eks_blueprints_kubernetes_addons"
  "helm_release.aws_load_balancer_controller"
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

export TF_WORKSPACE=$CLUSTER_NAME
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "null" ]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

terraform init --upgrade

# refresh once
terraform refresh -var="cluster_name=$CLUSTER_NAME"

for target in "${targets[@]}"
do
  echo "deleting ${target}"
  terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" -target="$target"
done

# sync the state file with the infrastructure resources
# this does not modify the infrastructure
echo "deleting the remaining resources"
terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME"

# NOTE: to clean up kubeconfig file used for "local-exec"
# rm -f /tmp/$CLUSTER_NAME.kubeconfig
