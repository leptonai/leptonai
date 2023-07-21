#!/bin/bash

# TODO: remove the default values set in install.sh so we use the default values in
# variables.tf: use the style of setting deployment-environment in this file
APPLY_FLAGS=(
    "-auto-approve"
    "-var=cluster_name=$CLUSTER_NAME"
    "-var=namespace=ws-$WORKSPACE_NAME"
    "-var=workspace_name=$WORKSPACE_NAME"
    "-var=oidc_id=$OIDC_ID"
    "-var=api_token=$API_TOKEN"
    "-var=image_tag_web=$IMAGE_TAG"
    "-var=image_tag_api_server=$IMAGE_TAG"
    "-var=image_tag_deployment_operator=$IMAGE_TAG"
    "-var=lepton_web_enabled=$WEB_ENABLED"
    "-var=create_efs=$CREATE_EFS"
    "-var=vpc_id=$VPC_ID"
    "-var=efs_mount_targets=$EFS_MOUNT_TARGETS"
    "-var=quota_group=$QUOTA_GROUP"
)

if [[ "$TLS_CERT_ARN_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=tls_cert_arn_id=$TLS_CERT_ARN_ID")
fi

if [[ "$ROOT_DOMAIN" != "" ]]; then
    APPLY_FLAGS+=("-var=root_domain=$ROOT_DOMAIN")
fi

# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars
if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var-file=deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars")
fi
