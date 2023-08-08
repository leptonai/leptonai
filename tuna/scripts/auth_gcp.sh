#!/bin/bash

set -e

script_path=$(python -c "import os; print(os.path.realpath('$0'))")
scripts_dir=$(dirname ${script_path})
top_dir=$(dirname ${scripts_dir})


echo "Authenticating to GCP"
if [[ ! -e ${top_dir}/.google_application_credentials ]]; then
    echo "You need to put google application credentials file at ${top_dir}/.google_application_credentials"
    exit 1
fi
gcloud auth activate-service-account --key-file ${top_dir}/.google_application_credentials
yes | gcloud config set project lepton-dev
gcloud auth configure-docker us-west1-docker.pkg.dev
echo "Done"
