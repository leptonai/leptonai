#! /usr/bin/env bash

must_create_workspace() {
  local http_response
  http_response=$(curl \
    --silent \
    --output /dev/null \
    --write-out "%{http_code}" \
    --header "Authorization: Bearer $2" \
    --header "Content-Type: application/vnd.api+json" \
    --request POST \
    --data '{
      "data": {
        "type": "workspaces",
        "attributes": {
          "name": "'"$1"'",
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
