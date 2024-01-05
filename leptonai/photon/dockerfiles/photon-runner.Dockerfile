ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY . /tmp/leptonai-sdk
RUN pip install /tmp/leptonai-sdk
RUN rm -rf /tmp/leptonai-sdk

WORKDIR /workspace
