#!/bin/bash

# List of Terraform modules to apply in sequence
targets=(
  "module.vpc"
  "module.eks"
)

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $CLUSTER_NAME ]]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

export "TF_WORKSPACE"=$CLUSTER_NAME

echo "Creating cluster $CLUSTER_NAME..."
must_create_workspace() {
  local http_response=$(curl \
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
    if [ $http_response -eq 201 ] || [ $http_response -eq 422 ]; then
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
