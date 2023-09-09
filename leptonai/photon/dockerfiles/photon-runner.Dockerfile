ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN CT_CUBLAS=1 pip install ctransformers -U --no-binary ctransformers --no-cache-dir

COPY . /tmp/leptonai-sdk
RUN pip install /tmp/leptonai-sdk
RUN rm -rf /tmp/leptonai-sdk

WORKDIR /workspace
