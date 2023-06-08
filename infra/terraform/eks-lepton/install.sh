#!/bin/bash

CLUSTER_NAME=$1

# List of Terraform modules to apply in sequence
targets=(
  "module.vpc"
  "module.eks"
)

# Initialize Terraform
terraform init --upgrade

# Apply modules in sequence
for target in "${targets[@]}"
do
  if [[ -z $API_TOKEN ]]; then
    echo "Applying module $target, no API token specified"
  else
    echo "Applying module $target, API token = $API_TOKEN"
  fi
  terraform apply -target="$target" -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="api_token=$API_TOKEN"
  apply_output=$(terraform apply -target="$target" -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="api_token=$API_TOKEN" 2>&1)
  if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
    echo "SUCCESS: Terraform apply of $target completed successfully"
  else
    echo "FAILED: Terraform apply of $target failed"
    exit 1
  fi
done

# Final apply to catch any remaining resources
echo "Applying remaining resources..."
terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="api_token=$API_TOKEN"
apply_output=$(terraform apply -auto-approve -var="cluster_name=$CLUSTER_NAME" -var="api_token=$API_TOKEN" 2>&1)
if [[ $? -eq 0 && $apply_output == *"Apply complete"* ]]; then
  echo "SUCCESS: Terraform apply of all modules completed successfully"
else
  echo "FAILED: Terraform apply of all modules failed"
  exit 1
fi
