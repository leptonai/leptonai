FROM python:3.10-alpine

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN rm /tmp/requirements.txt

RUN apk update
RUN apk add --no-cache git
RUN pip install git+https://github.com/bddppq/flower.git
