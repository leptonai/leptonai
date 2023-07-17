#!/bin/bash

APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME")

if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var=deployment_environment=$DEPLOYMENT_ENVIRONMENT")
fi
