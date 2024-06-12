ARG ROCM_VERSION=5.6
ARG UBUNTU_VERSION=22.04

FROM rocm/dev-ubuntu-${UBUNTU_VERSION}:${ROCM_VERSION}

ARG ROCM_VERSION=5.6
ARG PYTHON_VERSION
RUN if [ -z "$PYTHON_VERSION" ]; then \
    echo "PYTHON_VERSION is not set"; \
    exit 1; \
    fi

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

COPY . /tmp/leptonai-sdk

ENV LEPTON_VIRTUAL_ENV=/opt/lepton/venv

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_base.sh

RUN sudo apt-get update && sudo apt-get install -y libgl1 ffmpeg libgoogle-perftools-dev
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4"

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_python.sh ${PYTHON_VERSION}
ENV PATH="$LEPTON_VIRTUAL_ENV/bin:$PATH"

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_jupyter.sh

RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm${ROCM_VERSION}

RUN pip install uvicorn[standard] gradio!=3.31.0

RUN rm -rf /tmp/leptonai-sdk
