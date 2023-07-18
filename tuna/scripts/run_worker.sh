#!/bin/bash

set -e

script_path=$(python -c "import os; print(os.path.realpath('$0'))")
scripts_dir=$(dirname ${script_path})
top_dir=$(dirname ${scripts_dir})

cd ${top_dir}

if [[ ! -d "venv" ]]; then
    echo "'venv' directory does not exist. You need to run prepare_worker.sh script first"
    exit 1
fi

if hash conda 2>/dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate tuna
else
    source venv/bin/activate
fi
exec celery -A tuna worker -l INFO --concurrency=1
