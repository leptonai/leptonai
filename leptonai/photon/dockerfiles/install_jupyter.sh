#!/bin/bash

set -e

pip install notebook==6.5.7 jupyter_contrib_nbextensions==0.7.0 widgetsnbextension==4.0.11 jupyter-server==1.24.0
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
    echo "Jupyter Notebook started (port ${port})"
}

start_jupyter
sleep infinity
EOF
    chmod +x /usr/local/bin/start-jupyter
else
    echo "start-jupyter already exists"
fi
