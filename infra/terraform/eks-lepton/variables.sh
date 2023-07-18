#!/bin/bash

APPLY_FLAGS=("-auto-approve" "-var=cluster_name=$CLUSTER_NAME")

# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars
if [[ "$DEPLOYMENT_ENVIRONMENT" != "" ]]; then
    APPLY_FLAGS+=("-var-file=deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars")
fi

if [[ "$REGION" != "" ]]; then
    APPLY_FLAGS+=("-var=region=$REGION")
fi

if [[ "$DEFAULT_CAPACITY_TYPE" != "" ]]; then
    APPLY_FLAGS+=("-var=default_capacity_type=$DEFAULT_CAPACITY_TYPE")
fi

if [[ "$LEPTON_CLOUD_ROUTE53_ZONE_ID" != "" ]]; then
    APPLY_FLAGS+=("-var=lepton_cloud_route53_zone_id=$LEPTON_CLOUD_ROUTE53_ZONE_ID")
fi

if [[ "$SINGLE_NAT_GATEWAY" != "" ]]; then
    APPLY_FLAGS+=("-var=single_nat_gateway=$SINGLE_NAT_GATEWAY")
fi

if [[ "$USE_UBUNTU_NVIDIA_GPU_OPERATOR" != "" ]]; then
    APPLY_FLAGS+=("-var=use_ubuntu_nvidia_gpu_operator=$USE_UBUNTU_NVIDIA_GPU_OPERATOR")
fi
