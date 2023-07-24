#!/bin/bash

APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME")

# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars
if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var-file=deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars")
fi

if [[ "$AUTH_USERS_IAM_GROUP_NAME" != "" ]]; then
    APPLY_FLAGS+=("-var=auth_users_iam_group_name=$AUTH_USERS_IAM_GROUP_NAME")
fi

if [[ "$REGION" != "" ]]; then
    APPLY_FLAGS+=("-var=region=$REGION")
fi

if [[ "$LEPTON_CLOUD_ROUTE53_ZONE_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=lepton_cloud_route53_zone_id=$LEPTON_CLOUD_ROUTE53_ZONE_ID")
fi

if [[ "$ROOT_HOSTNAME" != "" ]]; then
    APPLY_FLAGS+=("-var=root_hostname=$ROOT_HOSTNAME")
fi

if [[ "$TLS_CERT_ARN_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=tls_cert_arn_id=$TLS_CERT_ARN_ID")
fi

if [[ "$AURORA_MASTER_USERNAME" != "" ]]; then
    APPLY_FLAGS+=("-var=aurora_master_username=$AURORA_MASTER_USERNAME")
fi

if [[ "$API_TOKEN" != "" ]]; then
    APPLY_FLAGS+=("-var=api_token=$API_TOKEN")
fi