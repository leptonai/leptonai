#!/bin/bash

set -e

script_path=$(python -c "import os; print(os.path.realpath('$0'))")
scripts_dir=$(dirname ${script_path})
top_dir=$(dirname ${scripts_dir})

cd ${top_dir}

echo "Checking CUDA installation"
if ! hash nvidia-smi 2>/dev/null; then
    echo "cuda (nvidia-smi) is not installed"
    $scripts_dir/install_cuda.sh
fi
echo "Done"

echo "Checking docker installation"
if ! hash docker 2>/dev/null; then
    echo "docker is not installed"
    $scripts_dir/install_docker.sh
fi
echo "Done"

echo "Checking docker image"
if [[ ! -e ${top_dir}/.google_application_credentials ]]; then
    echo "You need to put google application credentials file at ${top_dir}/.google_application_credentials"
    exit 1
fi
gcloud auth activate-service-account --key-file ${top_dir}/.google_application_credentials
gcloud config set project lepton-dev
gcloud auth configure-docker us-west1-docker.pkg.dev
docker pull us-west1-docker.pkg.dev/lepton-dev/tuna/fastchat:23.02
echo "Done"

echo "Checking model weights"
if [[ ! -d "lepton-llm" ]]; then
    echo "Downloading letpton-llm models"
    for model in "llama2/7b-chat" "vicuna/7B" "baichuan"; do
        if [[ -d "lepton-llm/${model}" ]]; then
            echo "lepton-llm/${model} already exists"
            continue
        fi
        echo "Downloading model ${model} to lepton-llm/${model}"
        mkdir -p lepton-llm/${model}
        gsutil -m rsync -r gs://lepton-llm/tuna-ready/${model}/ lepton-llm/${model}
    done
fi
echo "Done"

echo "Checking virtual environment"
if hash conda 2>/dev/null; then
    if ! conda env list | grep tuna; then
	echo "creating conda environment"
	conda create --name tuna python=3.10
    fi
    eval "$(conda shell.bash hook)"
    conda activate tuna
else
    if [[ ! -d "venv" ]]; then
	echo "creating virtual environment"
	python3 -m venv venv
    fi
    source venv/bin/activate
fi
pip install -U pip setuptools
pip install -r requirements.txt
echo "Done"
