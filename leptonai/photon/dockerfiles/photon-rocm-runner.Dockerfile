ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY . /tmp/leptonai-sdk

RUN /tmp/leptonai-sdk/leptonai/photon/dockerfiles/install_rocm_common_python_libraries.sh

RUN pip install /tmp/leptonai-sdk

RUN rm -rf /tmp/leptonai-sdk

WORKDIR /workspace

