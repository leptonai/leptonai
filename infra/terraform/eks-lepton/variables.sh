#!/bin/bash

ENABLE_AMAZON_MANAGED_PROMETHEUS=${ENABLE_AMAZON_MANAGED_PROMETHEUS:-false}
APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME" "-var=enable_amazon_managed_prometheus=$ENABLE_AMAZON_MANAGED_PROMETHEUS")

if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var=deployment_environment=$DEPLOYMENT_ENVIRONMENT")
fi
