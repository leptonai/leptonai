#!/bin/bash

set -e

apt-get update
apt-get install -y sudo software-properties-common build-essential tzdata git openssh-server
apt-get install -y libxml2-dev libxslt1-dev python3-dev
