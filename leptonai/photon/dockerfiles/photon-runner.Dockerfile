ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# TODO: Should move to base image
RUN sudo apt-get update && sudo apt-get install -y libgl1 ffmpeg libgoogle-perftools-dev
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4"

RUN pip install -U pip setuptools wheel

RUN CT_CUBLAS=1 pip install ctransformers -U --no-binary ctransformers --no-cache-dir

COPY . /tmp/leptonai-sdk
RUN pip install /tmp/leptonai-sdk
RUN rm -rf /tmp/leptonai-sdk

WORKDIR /workspace
