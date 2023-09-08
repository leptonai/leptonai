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

terraform init --upgrade
echo "SUCCESS: Terraform init completed successfully"

# loads additional flags and values for the following "terraform apply" commands
# shellcheck source=/dev/null
source ./variables.sh

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.install.log"

# Apply modules in sequence
for target in "${targets[@]}"
do
  terraform apply -target="$target" "${APPLY_FLAGS[@]}"
  echo "SUCCESS: Terraform apply of $target completed successfully"
done

# Final apply to catch any remaining resources
terraform apply "${APPLY_FLAGS[@]}"
echo "SUCCESS: Terraform apply of all modules completed successfully"
