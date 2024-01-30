ARG ROCM_VERSION=5.7
ARG UBUNTU_VERSION=22.04

FROM rocm/dev-ubuntu-${UBUNTU_VERSION}:${ROCM_VERSION}

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

COPY . /tmp/leptonai-sdk

ARG PYTHON_VERSION
ENV LEPTON_VIRTUAL_ENV=/opt/lepton/venv

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_base.sh

RUN sudo apt-get update && sudo apt-get install -y libgl1 ffmpeg libgoogle-perftools-dev
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4"

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_python.sh ${PYTHON_VERSION}
ENV PATH="$LEPTON_VIRTUAL_ENV/bin:$PATH"

RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm${ROCM_VERSION}

RUN pip install uvicorn[standard] gradio!=3.31.0

RUN CT_HIPBLAS=1 pip install ctransformers -U --no-binary ctransformers --no-cache-dir

RUN rm -rf /tmp/leptonai-sdk
