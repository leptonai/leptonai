#!/bin/bash

APPLY_FLAGS="-var-file=accounts.tfvars"

if [[ "$AUTO_APPROVE" == "true" ]]; then
    APPLY_FLAGS="${APPLY_FLAGS} -auto-approve"
fi

if [[ "$ENVIRONMENT" == "prod" ]]; then
    APPLY_FLAGS="${APPLY_FLAGS} -var-file=prod.tfvars"
elif [[ "$ENVIRONMENT" == "dev" ]]; then
    APPLY_FLAGS="${APPLY_FLAGS} -var-file=dev.tfvars"
fi
