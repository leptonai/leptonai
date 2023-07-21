ARG CUDA_VERSION=11.7.0
ARG CUDNN_VERSION=8
ARG UBUNTU_VERSION=22.04

FROM nvcr.io/nvidia/cuda:${CUDA_VERSION}-cudnn${CUDNN_VERSION}-devel-ubuntu${UBUNTU_VERSION}

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

COPY . /tmp/lepton/

ARG PYTHON_VERSION
ENV LEPTON_VIRTUAL_ENV=/opt/lepton/venv
RUN /tmp/lepton/sdk/leptonai/photon/dockerfiles/install_base.sh
RUN /tmp/lepton/sdk/leptonai/photon/dockerfiles/install_python.sh ${PYTHON_VERSION}
ENV PATH="$LEPTON_VIRTUAL_ENV/bin:$PATH"

RUN pip install /tmp/lepton/sdk
RUN pip install -U uvicorn[standard] gradio!=3.31.0
RUN rm -rf /tmp/lepton

WORKDIR /workspace
