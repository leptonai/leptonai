#!/bin/bash

set -e

die() {
  echo "$@" >&2
  exit 1
}

usage() {
  die "Usage: $0 ${JUPYTER_VERSION}"
}

if [ $# -ne 1 ]; then
  usage
fi

jupyter_version=$1
echo "Jupyter Version is ${jupyter_version}"

pip install notebook==${jupyter_version} jupyter_contrib_nbextensions widgetsnbextension
jupyter contrib nbextension install --system
jupyter nbextension enable --py widgetsnbextension

if [ ! -f /usr/local/bin/start-jupyter ]; then
    cat >/usr/local/bin/start-jupyter <<'EOF'
start_jupyter() {
    if [[ -z $JUPYTER_PASSWORD ]]; then
        echo "JUPYTER_PASSWORD must be set"
        exit 1
    fi
    local port=${JUPYTER_PORT:-18888}
    echo "Starting Jupyter Notebook..."
    jupyter notebook --allow-root --no-browser --port=${port} --ip=* --FileContentsManager.delete_to_trash=False --NotebookApp.terminado_settings='{"shell_command":["/bin/bash"]}' --NotebookApp.token=${JUPYTER_PASSWORD} --NotebookApp.allow_origin=* --NotebookApp.preferred_dir=/workspace &> /jupyter.log &
    echo "Jupyter Notebook started"
}

start_jupyter
sleep infinity
EOF
    chmod +x /usr/local/bin/start-jupyter
else
    echo "start-jupyter already exists"
fi
