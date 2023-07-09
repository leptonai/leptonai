#!/bin/bash

set -xe

# List of Terraform modules/resources to apply in sequence
# setting up gp3/2 storage class before anything else
# to set gp3 as default
targets=(
  "time_static.activation_date"

  "module.vpc"

  "aws_security_group.eks"
  "aws_security_group.nodes"
  "aws_security_group_rule.nodes"
  "aws_security_group_rule.ingress_from_node_to_cluster"
  "aws_security_group.alb_shared_backend"

  "module.eks"
  "kubernetes_storage_class_v1.gp3_sc_default"
  "kubernetes_annotations.gp2_sc_non_default"
  "module.ebs_csi_driver_irsa"
  "helm_release.gpu-operator"

  # bug https://github.com/hashicorp/terraform-provider-kubernetes/issues/1917
  # need to apply this first to avoid network policy CRD creation error, [depend on] does not work
  "helm_release.calico"

  "module.eks_blueprints_kubernetes_addons"
)

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi
echo "Creating cluster $CLUSTER_NAME..."

# shellcheck source=/dev/null
source ../lib.sh

# NOTE: we want to enforce terraform workspace
if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi
export TF_WORKSPACE=$CLUSTER_NAME
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

echo "creating terraform workspace ${TF_WORKSPACE}"
must_create_workspace "$TF_WORKSPACE" "$TF_API_TOKEN"

if terraform init --upgrade ; then
  echo "SUCCESS: Terraform init completed successfully"
else
  echo "ERROR: Terraform init failed"
  exit 1
fi

CHECK_TERRAFORM_APPLY_OUTPUT=${CHECK_TERRAFORM_APPLY_OUTPUT:-true}
ENABLE_AMAZON_MANAGED_PROMETHEUS=${ENABLE_AMAZON_MANAGED_PROMETHEUS:-false}

# Apply modules in sequence
for target in "${targets[@]}"
do
  terraform apply -target="$target" -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="enable_amazon_managed_prometheus=$ENABLE_AMAZON_MANAGED_PROMETHEUS"

  if [[ "$CHECK_TERRAFORM_APPLY_OUTPUT" == "true" ]]; then
    apply_output=$(terraform apply -target="$target" -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="enable_amazon_managed_prometheus=$ENABLE_AMAZON_MANAGED_PROMETHEUS" 2>&1)
    if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
      echo "SUCCESS: Terraform apply of $target completed successfully"
    else
      echo "FAILED: Terraform apply of $target failed"
      exit 1
    fi
  fi
done

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

# Final apply to catch any remaining resources
echo "Applying remaining resources..."
terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="enable_amazon_managed_prometheus=$ENABLE_AMAZON_MANAGED_PROMETHEUS"

if [[ "$CHECK_TERRAFORM_APPLY_OUTPUT" == "true" ]]; then
  apply_output=$(terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="enable_amazon_managed_prometheus=$ENABLE_AMAZON_MANAGED_PROMETHEUS" 2>&1)
  if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
    echo "SUCCESS: Terraform apply of all modules completed successfully"
  else
    echo "FAILED: Terraform apply of all modules failed"
    exit 1
  fi
fi

echo ""
echo "Run this to access the cluster:"
echo "aws eks update-kubeconfig --region us-east-1 --name $CLUSTER_NAME --kubeconfig /tmp/$CLUSTER_NAME.kubeconfig"
echo ""
echo "APPLY SUCCESS"
