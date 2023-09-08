#!/usr/bin/env bash
set -xue

if ! [[ "$0" =~ hack/gen.openapi.lamba-labs.sh ]]; then
    echo "must be run from repository root"
    exit 255
fi

# https://github.com/OpenAPITools/openapi-generator#16---docker
# https://cloud.lambdalabs.com/api/v1/docs
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
-i https://cloud.lambdalabs.com/static/api/v1/openapi.yaml \
-g go \
-o /local/go-pkg/openapi/lambdalabs \
--package-name lambdalabs
