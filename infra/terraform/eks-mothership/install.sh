#!/bin/bash

set -xe

# List of Terraform modules/resources to apply in sequence
targets=(
  "time_static.activation_date"
  "module.vpc"
  "module.eks"
  "kubernetes_storage_class_v1.gp3_sc_default"
  "kubernetes_annotations.gp2_sc_non_default"
  "aws_eks_addon.csi_ebs"
  "helm_release.alb_controller"
  "helm_release.external_dns"
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
export TF_WORKSPACE="mo-$CLUSTER_NAME"
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

echo "creating terraform workspace ${TF_WORKSPACE}"
must_create_workspace "$TF_WORKSPACE" "$TF_API_TOKEN"

if terraform init --upgrade ; then
  echo "SUCCESS: Terraform init completed successfully"
else
  echo "ERROR: Terraform init failed"
  exit 1
fi

# loads additional flags and values for the following "terraform apply" commands
# shellcheck source=/dev/null
source ./variables.sh

export TF_LOG="DEBUG"
export TF_LOG_PATH="tf.install.log"

CHECK_TERRAFORM_APPLY_OUTPUT="${CHECK_TERRAFORM_APPLY_OUTPUT:-true}"

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

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
# we're not running install.sh via mothership, thus requiring manual copy
ENABLE_COPY_LEPTON_CHARTS=${ENABLE_COPY_LEPTON_CHARTS:-true}
if [[ "$ENABLE_COPY_LEPTON_CHARTS" == "true" ]]; then
  echo "copying lepton charts from ../../../charts/mothership"
  rm -rf ./charts && mkdir -p ./charts
  cp -r ../../../charts/mothership ./charts/
  cp ../../../mothership/crd/config/crd/bases/*.yaml ./charts/mothership/templates/
else
  echo "skipping copying lepton charts"
fi

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
