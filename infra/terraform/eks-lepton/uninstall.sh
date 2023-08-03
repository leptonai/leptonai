#!/bin/bash

set -x

# List of Terraform modules/resources to destroy in sequence (reverse order of apply)
# need to delete existing kubernetes resources to avoid dependency conflicts
#
# NOTE
# s3/roles can be deleted at the end since it does not cause any conflicts
#
# NOTE
# "aws_acm_certificate" depends on the EKS cluster load balancer
# so we need to delete the EKS cluster first
targets=(
  "null_resource.delete_all_lepton_deployments_and_ingresses"
  "helm_release.lepton_crd"
  "helm_release.lepton"

  # bug https://github.com/tigera/operator/issues/2031
  "null_resource.delete_calico_installation"

  "helm_release.kube_prometheus_stack"
  "helm_release.gloo_edge"
)

if [ -z "$CLUSTER_NAME" ]; then
  CLUSTER_NAME=$(terraform output -json | jq -r '.cluster_name.value')
fi

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $TF_WORKSPACE ]]; then
  export TF_WORKSPACE="cl-$CLUSTER_NAME-default"
else
  export TF_WORKSPACE
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "null" ]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

if terraform init --upgrade ; then
  echo "SUCCESS: Terraform init completed successfully"
else
  echo "ERROR: Terraform init failed"
  exit 1
fi

# only copy CRDs if UNINSTALL_CRDS is true
UNINSTALL_CRDS=${UNINSTALL_CRDS:-false}
if [[ "$UNINSTALL_CRDS" == "true" ]]; then
  echo "copying lepton CRDs from ../../../deployment-operator/config/crd/bases"
  cp ../../../deployment-operator/config/crd/bases/*.yaml ./charts/lepton/templates/
fi

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.uninstall.log"

DEPLOYMENT_ENVIRONMENT=${DEPLOYMENT_ENVIRONMENT:-TEST}
REGION=${REGION:-"us-east-1"}
for target in "${targets[@]}"
do
  echo "deleting ${target}"
  terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" -target="$target"
done

echo "deleting the remaining resources"
if terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" ; then
  echo "SUCCESS: Terraform destroy completed successfully"
else
  echo "FAILED: Terraform destroy failed"
  exit 1
fi

# NOTE: to clean up kubeconfig file used for "local-exec"
# rm -f /tmp/$CLUSTER_NAME.kubeconfig
