#!/bin/bash

AURORA_MASTER_USERNAME=${AURORA_MASTER_USERNAME:-root}
APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME" "-var=aurora_master_username=$AURORA_MASTER_USERNAME")

if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var=deployment_environment=$DEPLOYMENT_ENVIRONMENT")
fi
