FROM nvcr.io/nvidia/pytorch:23.04-py3

ARG DEBIAN_FRONTEND=noninteractive

COPY . /tmp/lepton/
RUN pip install /tmp/lepton
RUN pip install -r /tmp/lepton/lepton/requirements.txt
RUN pip install -U uvicorn[standard] gradio
RUN rm -rf /tmp/lepton
