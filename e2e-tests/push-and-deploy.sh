#! /bin/sh

set -e
set -x

NAMESPACE=$1
if [ -z "$NAMESPACE" ]; then
    echo "No namespace provided"
    exit 1
fi

TOKEN=$2
if [ -z "$TOKEN" ]; then
    echo "No token provided: continuing without auth token"
fi

REMOTE=$3
if [ -z "$REMOTE" ]; then
    echo "No remote url provided"
    exit 1
fi

# run up to 60-minute as we add more e2e tests for example models
if ! COLUMNS=2000 go test -timeout 3600s -v ./e2e-tests/... --remote-url "$REMOTE" --auth-token "$TOKEN"; then
    exit 1
fi
