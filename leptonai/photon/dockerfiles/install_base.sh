#!/bin/bash

set -e

apt-get update
apt-get install -y sudo software-properties-common build-essential tzdata git openssh-server
