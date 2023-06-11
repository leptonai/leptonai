#!/bin/bash

set -xue

# List of Terraform modules/resources to destroy in sequence (reverse order of apply)
# need to delete existing kubernetes resources to avoid dependency conflicts
#
# NOTE
# s3/roles can be deleted at the end since it does not cause any conflicts
#
# NOTE
# "aws_acm_certificate" depends on the EKS cluster load balancer
# so we need to delete the EKS cluster first
#
# TODO
# destroying "module.eks_blueprints_kubernetes_addons" may not work, some pods stuck in Terminating
# workarounds can be found here https://github.com/leptonai/lepton/issues/546
# until we automate those
targets=(
  "helm_release.lepton"
  "module.eks_blueprints_kubernetes_addons"
  "helm_release.gpu-operator"
  "helm_release.aws_load_balancer_controller"
  "module.ebs_csi_driver_irsa"
  "module.eks"
  "aws_acm_certificate.cert"
  "aws_route53_record.cert-record"
  "module.vpc"
)

if [ -z "$CLUSTER_NAME" ]; then
  CLUSTER_NAME=$(terraform output -json | jq -r '.cluster_name.value')
fi

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

export "TF_WORKSPACE"=$CLUSTER_NAME

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
