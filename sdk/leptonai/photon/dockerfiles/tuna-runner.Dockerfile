ARG FASTCHAT_VERSION=23.02
FROM 605454121064.dkr.ecr.us-east-1.amazonaws.com/fastchat:${FASTCHAT_VERSION}

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

COPY . /tmp/lepton

RUN pip install /tmp/lepton/sdk
RUN pip install -U uvicorn[standard]
RUN rm -rf /tmp/lepton
