#! /bin/sh

set -e
set -x

TOKEN=$1
if [ -z "$TOKEN" ]; then
    echo "No token provided: continuing without auth token"
fi

WORKSPACE_URL=$2
if [ -z "$WORKSPACE_URL" ]; then
    echo "No workspace url provided"
    exit 1
fi

# run up to 60-minute as we add more e2e tests for example models
if ! COLUMNS=2000 go test -timeout 3600s -v ./e2e-tests/... --workspace-url "$WORKSPACE_URL" --auth-token "$TOKEN"; then
    exit 1
fi
