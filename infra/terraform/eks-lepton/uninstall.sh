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
#
# NOTE
# destroying "module.eks_blueprints_addons" may not work, some pods stuck in Terminating
# workarounds can be found here https://github.com/leptonai/lepton/issues/546 and implemented using local-exec
# TODO: Can we remove those hacks with custom terraform provider?
targets=(
  "null_resource.delete_all_lepton_deployments_and_ingresses"
  "helm_release.lepton_crd"
  "helm_release.lepton"

  # bug https://github.com/tigera/operator/issues/2031
  "null_resource.delete_calico_installation"

  "helm_release.kube_prometheus_stack"
  "module.eks_blueprints_addons"
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

if terraform init --upgrade ; then
  echo "SUCCESS: Terraform init completed successfully"
else
  echo "ERROR: Terraform init failed"
  exit 1
fi

for target in "${targets[@]}"
do
  echo "deleting ${target}"
  terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" -target="$target"
done

echo "deleting the remaining resources"
if terraform apply -destroy -auto-approve -var="cluster_name=$CLUSTER_NAME" ; then
  echo "SUCCESS: Terraform destroy completed successfully"
else
  echo "FAILED: Terraform destroy failed"
  exit 1
fi

# NOTE: to clean up kubeconfig file used for "local-exec"
# rm -f /tmp/$CLUSTER_NAME.kubeconfig
