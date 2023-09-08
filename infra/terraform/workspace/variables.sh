#!/bin/bash

# TODO: remove the default values set in install.sh so we use the default values in
# variables.tf: use the style of setting deployment-environment in this file
APPLY_FLAGS=(
    "-auto-approve"
    "-var=cluster_name=$CLUSTER_NAME"
    "-var=namespace=ws-$WORKSPACE_NAME"
    "-var=workspace_name=$WORKSPACE_NAME"
    "-var=tier=$WORKSPACE_TIER"
    "-var=oidc_id=$OIDC_ID"
    "-var=api_token=$API_TOKEN"
    "-var=image_tag_web=$IMAGE_TAG"
    "-var=image_tag_api_server=$IMAGE_TAG"
    "-var=image_tag_deployment_operator=$IMAGE_TAG"
    "-var=lepton_web_enabled=$WEB_ENABLED"
    "-var=create_efs=$CREATE_EFS"
    "-var=vpc_id=$VPC_ID"
    "-var=efs_mount_targets=$EFS_MOUNT_TARGETS"
)

if [[ "$ENABLE_QUOTA" != "" ]]; then
    APPLY_FLAGS+=("-var=enable_quota=$ENABLE_QUOTA")
fi

if [[ "$LB_TYPE" != "" ]]; then
    APPLY_FLAGS+=("-var=lb_type=$LB_TYPE")
fi

if [[ "$SHARED_ALB_MAIN_DOMAIN" != "" ]]; then
    APPLY_FLAGS+=("-var=shared_alb_main_domain=$SHARED_ALB_MAIN_DOMAIN")
fi

if [[ "$QUOTA_CPU" != "" ]]; then
    APPLY_FLAGS+=("-var=quota_cpu=$QUOTA_CPU")
fi

if [[ "$QUOTA_MEMORY" != "" ]]; then
    APPLY_FLAGS+=("-var=quota_memory=$QUOTA_MEMORY")
fi

if [[ "$QUOTA_GPU" != "" ]]; then
    APPLY_FLAGS+=("-var=quota_gpu=$QUOTA_GPU")
fi

if [[ "$REGION" != "" ]]; then
    APPLY_FLAGS+=("-var=region=$REGION")
fi

if [[ "$TLS_CERT_ARN_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=tls_cert_arn_id=$TLS_CERT_ARN_ID")
fi

if [[ "$ROOT_DOMAIN" != "" ]]; then
    APPLY_FLAGS+=("-var=root_domain=$ROOT_DOMAIN")
fi

if [[ "$STATE" != "" ]]; then
    APPLY_FLAGS+=("-var=state=$STATE")
fi

# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars
if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var-file=deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars")
fi

if [[ "$UPDATED_UNIX_TIME_RFC3339" != "" ]]; then
    APPLY_FLAGS+=("-var=updated_unix_time_rfc3339=$UPDATED_UNIX_TIME_RFC3339")
fi
