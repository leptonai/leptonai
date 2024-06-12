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

pip install notebook==${jupyter_version}
jupyter contrib nbextension install --system
jupyter nbextension enable --py widgetsnbextension

if [ ! -f /usr/local/bin/start-jupyter ]; then
    cat >/usr/local/bin/start-jupyter <<'EOF'
start_jupyter() {
    if [[ $JUPYTER_PASSWORD ]]; then
        echo "Starting Jupyter Lab..."
        mkdir -p /workspace && \
        cd / && \
        nohup jupyter lab --allow-root --no-browser --port=18888 --ip=* --FileContentsManager.delete_to_trash=False --ServerApp.terminado_settings='{"shell_command":["/bin/bash"]}' --ServerApp.token=$JUPYTER_PASSWORD --ServerApp.allow_origin=* --ServerApp.preferred_dir=/workspace &> /jupyter.log &
        echo "Jupyter Lab started"
    fi
}

start_jupyter
sleep infinity
EOF
    chmod +x /usr/local/bin/start-jupyter
else
    echo "start-jupyter already exists"
fi
