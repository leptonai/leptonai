#!/bin/bash

ENABLE_AMAZON_MANAGED_PROMETHEUS=${ENABLE_AMAZON_MANAGED_PROMETHEUS:-false}
export APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME" "-var=enable_amazon_managed_prometheus=$ENABLE_AMAZON_MANAGED_PROMETHEUS")

# TODO: add more conditions for node groups
