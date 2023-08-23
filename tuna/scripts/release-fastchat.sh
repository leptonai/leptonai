#!/bin/bash

set -e

script_path=$(python -c "import os; print(os.path.realpath('$0'))")
scripts_dir=$(dirname ${script_path})
tuna_top_dir=$(dirname ${scripts_dir})
top_dir=$(dirname ${tuna_top_dir})

cd ${tuna_top_dir}

dockerfiles_dir="${tuna_top_dir}/dockerfiles"

usage() {
    echo "Usage: $0 -f [fastchat-version]"
    echo "  -f fastchat version: e.g. 23.04"
    echo "  -h|--help: print this message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -f)
            shift
            if [[ $# -eq 0 ]]; then
                echo "Missing fastchat version"
                usage
            fi
            FASTCHAT_VERSION=$1
            shift
            ;;
        *)
            echo "Unknown option '$1'"
            usage
    esac
done

if [[ -z $FASTCHAT_VERSION ]]; then
    echo "Missing fastchat version"
    usage
fi

bash "${scripts_dir}/auth_gcp.sh"

echo "Fastchat version: $FASTCHAT_VERSION"
source_image="605454121064.dkr.ecr.us-east-1.amazonaws.com/fastchat:$FASTCHAT_VERSION"
echo "Pulling source image ${source_image}"
docker pull "${source_image}"

echo "Pushing source image to gcp"
docker tag "${source_image}" "us-west1-docker.pkg.dev/lepton-dev/tuna/fastchat:${FASTCHAT_VERSION}"
docker push "us-west1-docker.pkg.dev/lepton-dev/tuna/fastchat:${FASTCHAT_VERSION}"
echo "Done"

echo "Building lepton tuna-runner image"
cd "${top_dir}"
docker build \
    --build-arg FASTCHAT_VERSION="${FASTCHAT_VERSION}" \
    -t "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-${FASTCHAT_VERSION}" \
    -f "${dockerfiles_dir}/tuna-runner.Dockerfile" \
    "${top_dir}"
echo "Done"

echo "Pushing to aws"
docker push "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-${FASTCHAT_VERSION}"
echo "Done"

echo "Pushing to gcp"
docker tag "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-${FASTCHAT_VERSION}" \
       "us-west1-docker.pkg.dev/lepton-dev/tuna/lepton:tuna-${FASTCHAT_VERSION}"
docker push "us-west1-docker.pkg.dev/lepton-dev/tuna/lepton:tuna-${FASTCHAT_VERSION}"
echo "Done"
