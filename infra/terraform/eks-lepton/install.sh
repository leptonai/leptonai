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
  "aws_security_group.alb_controller"

  "module.eks"
  "kubernetes_config_map.aws_auth"
  "kubernetes_config_map_v1_data.aws_auth"

  "kubernetes_storage_class_v1.gp3_sc_default"
  "kubernetes_annotations.gp2_sc_non_default"

  # add all these as "depends_on" of the next target
  # so we can create these node groups in parallel
  #
  # "aws_eks_node_group.al2_x86_64_ac_g4dnxlarge"
  # "aws_eks_node_group.al2_x86_64_ac_g52xlarge"
  # "aws_eks_node_group.al2_x86_64_cpu_m6a16xlarge"
  # "aws_eks_node_group.ubuntu_x86_64_ac_g4dnxlarge"
  # "aws_eks_node_group.ubuntu_x86_64_ac_g52xlarge"
  # "aws_eks_node_group.ubuntu_x86_64_cpu_m6a16xlarge"

  "aws_eks_addon.csi_ebs"
  "helm_release.csi_efs"

  "helm_release.nvidia_gpu_operator"
  "helm_release.external_dns"

  # bug https://github.com/hashicorp/terraform-provider-kubernetes/issues/1917
  # need to apply this first to avoid network policy CRD creation error, [depend on] does not work
  "helm_release.calico"

  "aws_eks_addon.kubecost"
  "helm_release.kube_prometheus_stack"
  "helm_release.gloo_edge"
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
if [[ -z $TF_WORKSPACE ]]; then
  export TF_WORKSPACE="cl-$CLUSTER_NAME-default"
else
  export TF_WORKSPACE
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

echo "creating terraform workspace ${TF_WORKSPACE}"
must_create_workspace "$TF_WORKSPACE" "$TF_API_TOKEN"

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
ENABLE_COPY_LEPTON_CHARTS=${ENABLE_COPY_LEPTON_CHARTS:-false}
if [[ "$ENABLE_COPY_LEPTON_CHARTS" == "true" ]]; then
  # this is not running via mothership, thus requiring manual copy
  echo "copying eks-lepton charts from ../../../charts"
  rm -rf ./charts && cp -r ../../../charts .
  echo "copying lepton CRDs from ../../../deployment-operator/config/crd/bases"
  cp ../../../deployment-operator/config/crd/bases/*.yaml ./charts/eks-lepton/templates/
else
  echo "skipping copying lepton charts"
fi

terraform init --upgrade

# loads additional flags and values for the following "terraform apply" commands
# shellcheck source=/dev/null
source ./variables.sh

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.install.log"

CHECK_TERRAFORM_APPLY_OUTPUT=${CHECK_TERRAFORM_APPLY_OUTPUT:-true}

# Apply modules in sequence
for target in "${targets[@]}"
do
  terraform apply -target="$target" "${APPLY_FLAGS[@]}"

  if [[ "$CHECK_TERRAFORM_APPLY_OUTPUT" == "true" ]]; then
    apply_output=$(terraform apply -target="$target" "${APPLY_FLAGS[@]}" 2>&1)
    if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
      echo "SUCCESS: Terraform apply of $target completed successfully"
    else
      echo "FAILED: Terraform apply of $target failed"
      exit 1
    fi
  fi
done

# Final apply to catch any remaining resources
echo "Applying remaining resources..."
terraform apply "${APPLY_FLAGS[@]}"

if [[ "$CHECK_TERRAFORM_APPLY_OUTPUT" == "true" ]]; then
  apply_output=$(terraform apply "${APPLY_FLAGS[@]}" 2>&1)
  if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
    echo "SUCCESS: Terraform apply of all modules completed successfully"
  else
    echo "FAILED: Terraform apply of all modules failed"
    exit 1
  fi
fi

echo ""
echo "Run this to access the cluster:"
if [[ "$REGION" != "" ]]; then
    echo "aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME --kubeconfig /tmp/$CLUSTER_NAME.kubeconfig"
else
    echo "aws eks update-kubeconfig --region us-east-1 --name $CLUSTER_NAME --kubeconfig /tmp/$CLUSTER_NAME.kubeconfig"
fi
echo ""
echo "APPLY SUCCESS"
