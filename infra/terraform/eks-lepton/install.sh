#!/bin/bash

set -xe

# List of Terraform modules/resources to apply in sequence
# setting up gp3/2 storage class before anything else
# to set gp3 as default
targets=(
  "module.vpc"
  "module.eks"
  "kubernetes_storage_class_v1.gp3_sc_default"
  "kubernetes_annotations.gp2_sc_non_default"
  "module.ebs_csi_driver_irsa"
  "null_resource.delete_all_lepton_deployments_and_ingresses"
  "null_resource.delete_prometheus"
  "null_resource.delete_grafana"
  "helm_release.gpu-operator"
  "module.eks_blueprints_kubernetes_addons"
)

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

export TF_WORKSPACE=$CLUSTER_NAME

echo "Creating cluster $CLUSTER_NAME..."
must_create_workspace() {
  local http_response
  http_response=$(curl \
    --silent \
    --output /dev/null \
    --write-out "%{http_code}" \
    --header "Authorization: Bearer $TF_API_TOKEN" \
    --header "Content-Type: application/vnd.api+json" \
    --request POST \
    --data '{
      "data": {
        "type": "workspaces",
        "attributes": {
          "name": "'"$TF_WORKSPACE"'",
          "organization": {
            "name": "'"lepton"'"
          },
          "execution-mode": "local"
        }
      }
    }' \
    "https://app.terraform.io/api/v2/organizations/lepton/workspaces")

  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    # 201 = Created, 422 = Already exists
    if [ "$http_response" -eq 201 ] || [ "$http_response" -eq 422 ]; then
      echo "Workspace created successfully!"
    else
      echo "Failed to create workspace. HTTP response code: $http_response"
      exit $exit_code
    fi
  else
    echo "Failed to create workspace."
    exit $exit_code
  fi
}

must_create_workspace

# initialize Terraform
terraform init --upgrade

# Apply modules in sequence
for target in "${targets[@]}"
do
  terraform apply -target="$target" -auto-approve -var="cluster_name=$CLUSTER_NAME"
  apply_output=$(terraform apply -target="$target" -auto-approve -var="cluster_name=$CLUSTER_NAME" 2>&1)
  if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
    echo "SUCCESS: Terraform apply of $target completed successfully"
  else
    echo "FAILED: Terraform apply of $target failed"
    exit 1
  fi
done

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
if [[ -z $COPY_LEPTON_CHARTS ]]; then
  echo "skipping copying lepton charts"
else
  # this is not running via mothership, thus requiring manual copy
  echo "copying lepton charts from ../../../charts/lepton"
  rm -rf ./lepton || true
  cp -r ../../../charts/lepton ./lepton
fi

# Final apply to catch any remaining resources
echo "Applying remaining resources..."
terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME"
apply_output=$(terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" 2>&1)
if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
  echo "SUCCESS: Terraform apply of all modules completed successfully"
else
  echo "FAILED: Terraform apply of all modules failed"
  exit 1
fi

echo ""
echo "Run this to access the cluster:"
echo "aws eks update-kubeconfig --region us-east-1 --name $CLUSTER_NAME --kubeconfig /tmp/$CLUSTER_NAME.kubeconfig"
echo ""
echo "SUCCESS ALL"
echo ""
