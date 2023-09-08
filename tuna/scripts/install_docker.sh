#!/bin/bash

set -ex

if [ ! -f /etc/lsb-release ]; then
    echo "This script is only for Ubuntu"
    exit 1
fi

# Reference: https://docs.docker.com/engine/install/ubuntu

echo "Setting up docker apt repository"
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
    "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Installing docker"
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Testing docker installation by running a simple hello-world container"
sudo docker run hello-world

echo "Adding user ${USER} to docker group (so you don't have to run docker command with sudo)"
sudo usermod -aG docker ${USER}
echo "You will need to re-login for the group change to take effect."
