#! /bin/sh

set -e
set -x

NAMESPACE=$1
if [ -z "$NAMESPACE" ]; then
    exit 1
fi

REMOTE=
# try getting the remote address for 1 minute
for i in $(seq 1 60); do
    REMOTE=$(kubectl -n "$NAMESPACE" get ingress lepton-api-server-ingress -o jsonpath='{.metadata.annotations.external-dns\.alpha\.kubernetes\.io/hostname}')
    if [ -n "$REMOTE" ]; then
        break
    fi
    sleep 1
done
if [ -z "$REMOTE" ]; then
    exit 1
fi

# try getting the IP of the remote address for 10 minutes
for i in $(seq 1 600); do
    if host "$REMOTE" > /dev/null; then
        break
    fi
    sleep 1
done
if ! host "$REMOTE" > /dev/null; then
    exit 1
fi

REMOTE=https://$REMOTE/api/v1


# run up to 20-minute as we add more e2e tests for example models
COLUMNS=2000 go test -timeout 1200s -v ./e2e-tests/... --remote-url "$REMOTE" --namespace "$NAMESPACE"
if [ $? -ne 0 ]; then
    eixt 1
fi
