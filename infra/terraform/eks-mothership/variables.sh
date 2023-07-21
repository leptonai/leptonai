#!/bin/bash

AURORA_MASTER_USERNAME=${AURORA_MASTER_USERNAME:-root}
APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME" "-var=aurora_master_username=$AURORA_MASTER_USERNAME")

if [[ "$REGION" != "" ]]; then
    APPLY_FLAGS+=("-var=region=$REGION")
fi

if [[ "$LEPTON_CLOUD_ROUTE53_ZONE_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=lepton_cloud_route53_zone_id=$LEPTON_CLOUD_ROUTE53_ZONE_ID")
fi

if [[ "$TLS_CERT_ARN_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=tls_cert_arn_id=$TLS_CERT_ARN_ID")
fi

if [[ "$ROOT_HOSTNAME" != "" ]]; then
    APPLY_FLAGS+=("-var=root_hostname=$ROOT_HOSTNAME")
fi
