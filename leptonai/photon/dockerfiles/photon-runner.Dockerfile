ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY . /tmp/lepton/
RUN pip install /tmp/lepton/sdk
RUN rm -rf /tmp/lepton

WORKDIR /workspace
