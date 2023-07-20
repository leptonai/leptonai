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

if [[ "$DISK_SIZE_IN_GB_FOR_NODE_GROUPS" != "" ]]; then
    APPLY_FLAGS+=("-var=disk_size_in_gb_for_node_groups=$DISK_SIZE_IN_GB_FOR_NODE_GROUPS")
fi

if [[ "$USE_UBUNTU_NVIDIA_GPU_OPERATOR" != "" ]]; then
    APPLY_FLAGS+=("-var=use_ubuntu_nvidia_gpu_operator=$USE_UBUNTU_NVIDIA_GPU_OPERATOR")
fi

if [[ "$UBUNTU_X86_64_AC_G4DNXLARGE_MIN_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=ubuntu_x86_64_ac_g4dnxlarge_min_size=$UBUNTU_X86_64_AC_G4DNXLARGE_MIN_SIZE")
fi

if [[ "$UBUNTU_X86_64_AC_G4DNXLARGE_MAX_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=ubuntu_x86_64_ac_g4dnxlarge_max_size=$UBUNTU_X86_64_AC_G4DNXLARGE_MAX_SIZE")
fi

if [[ "$UBUNTU_X86_64_AC_G52XLARGE_MIN_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=ubuntu_x86_64_ac_g52xlarge_min_size=$UBUNTU_X86_64_AC_G52XLARGE_MIN_SIZE")
fi

if [[ "$UBUNTU_X86_64_AC_G52XLARGE_MAX_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=ubuntu_x86_64_ac_g52xlarge_max_size=$UBUNTU_X86_64_AC_G52XLARGE_MAX_SIZE")
fi

if [[ "$UBUNTU_X86_64_CPU_M6A16XLARGE_MIN_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=ubuntu_x86_64_cpu_m6a16xlarge_min_size=$UBUNTU_X86_64_CPU_M6A16XLARGE_MIN_SIZE")
fi

if [[ "$UBUNTU_X86_64_CPU_M6A16XLARGE_MAX_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=ubuntu_x86_64_cpu_m6a16xlarge_max_size=$UBUNTU_X86_64_CPU_M6A16XLARGE_MAX_SIZE")
fi

# TODO: remove all these
# once ubuntu is stable
if [[ "$AL2_X86_64_AC_G4DNXLARGE_MIN_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=al2_x86_64_ac_g4dnxlarge_min_size=$AL2_X86_64_AC_G4DNXLARGE_MIN_SIZE")
fi

if [[ "$AL2_X86_64_AC_G4DNXLARGE_MAX_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=al2_x86_64_ac_g4dnxlarge_max_size=$AL2_X86_64_AC_G4DNXLARGE_MAX_SIZE")
fi

if [[ "$AL2_X86_64_AC_G52XLARGE_MIN_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=al2_x86_64_ac_g52xlarge_min_size=$AL2_X86_64_AC_G52XLARGE_MIN_SIZE")
fi

if [[ "$AL2_X86_64_AC_G52XLARGE_MAX_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=al2_x86_64_ac_g52xlarge_max_size=$AL2_X86_64_AC_G52XLARGE_MAX_SIZE")
fi

if [[ "$AL2_X86_64_CPU_M6A16XLARGE_MIN_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=al2_x86_64_cpu_m6a16xlarge_min_size=$AL2_X86_64_CPU_M6A16XLARGE_MIN_SIZE")
fi

if [[ "$AL2_X86_64_CPU_M6A16XLARGE_MAX_SIZE" != "" ]]; then
    APPLY_FLAGS+=("-var=al2_x86_64_cpu_m6a16xlarge_max_size=$AL2_X86_64_CPU_M6A16XLARGE_MAX_SIZE")
fi
