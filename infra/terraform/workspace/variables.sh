#!/bin/bash

# shellcheck disable=SC2155
export WORKSPACE_APPLY_FLAGS=$(cat << EOM
-auto-approve \
-var="cluster_name=$CLUSTER_NAME" \
-var="namespace=$WORKSPACE_NAME" \
-var="workspace_name=$WORKSPACE_NAME" \
-var="oidc_id=$OIDC_ID" \
-var="api_token=$API_TOKEN" \
-var="image_tag_web=$IMAGE_TAG" \
-var="image_tag_api_server=$IMAGE_TAG" \
-var="image_tag_deployment_operator=$IMAGE_TAG" \
-var="lepton_web_enabled=$WEB_ENABLED" \
-var="create_efs=$CREATE_EFS" \
-var="vpc_id=$VPC_ID" \
-var="efs_mount_targets=$EFS_MOUNT_TARGETS"
EOM
)
