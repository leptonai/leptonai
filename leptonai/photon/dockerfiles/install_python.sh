#!/bin/bash

set -e

die() {
  echo "$@" >&2
  exit 1
}

usage() {
  die "Usage: $0 PYTHON_VERSION"
}

if [ $# -ne 1 ]; then
  usage
fi

python_version=$1
echo "Python Version is ${python_version}"

sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt install -y python${python_version} python${python_version}-dev python${python_version}-venv python-is-python3
python${python_version} -m venv ${LEPTON_VIRTUAL_ENV}
${LEPTON_VIRTUAL_ENV}/bin/pip install -U pip setuptools wheel
