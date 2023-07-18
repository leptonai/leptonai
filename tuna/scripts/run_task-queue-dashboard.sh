#!/bin/bash

set -e

script_path=$(python -c "import os; print(os.path.realpath('$0'))")
scripts_dir=$(dirname ${script_path})
top_dir=$(dirname ${scripts_dir})
dockerfiles_dir=${top_dir}/dockerfiles

if ! hash docker 2>/dev/null; then
    echo "docker is not installed"
    exit 1
fi

cd ${top_dir}
exec docker compose -f ${dockerfiles_dir}/docker-compose-task-queue-dashboard.yml up --build
