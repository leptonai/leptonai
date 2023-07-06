#!/bin/bash

set -x

targets=(
    "aws-access"
    "eks-lepton"
    "eks-mothership"
    "workspace"
)

for target in "${targets[@]}"
do
    echo "cleaning up ${target}"
    rm -rf "${target}"/.terraform
    rm -rf "${target}"/.terraform.lock.hcl
    rm -rf "${target}"/charts
done
