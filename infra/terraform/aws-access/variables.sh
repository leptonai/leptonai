#!/bin/bash

APPLY_FLAGS=("-var-file=accounts.tfvars")

if [[ "$AUTO_APPROVE" == "true" ]]; then
    APPLY_FLAGS+=("-auto-approve")
fi

if [[ "$ENVIRONMENT" == "PROD" ]]; then
    APPLY_FLAGS+=("-var-file=PROD.tfvars")
elif [[ "$ENVIRONMENT" == "DEV" ]]; then
    APPLY_FLAGS+=("-var-file=DEV.tfvars")
fi

if [[ "$CREATED_UNIX_TIME_RFC3339" != "" ]]; then
    APPLY_FLAGS+=("-var=created_unix_time_rfc3339=$CREATED_UNIX_TIME_RFC3339")
fi
