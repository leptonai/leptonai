#!/bin/bash

set -ex

if [ ! -f /etc/lsb-release ]; then
    echo "This script is only for Ubuntu"
    exit 1
fi

# Reference: https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=22.04&target_type=runfile_local

echo "Downloading CUDA Toolkit 12.1"
wget https://developer.download.nvidia.com/compute/cuda/12.1.1/local_installers/cuda_12.1.1_530.30.02_linux.run

echo "Installing CUDA Toolkit"
sudo sh cuda_12.1.1_530.30.02_linux.run

echo "Testing CUDA Toolkit"
nvidia-smi
echo "Finished installing CUDA Toolkit"

echo "Remove CUDA Toolkit installer"
rm cuda_12.1.1_530.30.02_linux.run

if ! hash docker 2>/dev/null; then
    echo "Docker not installed. Skipping NVIDIA Container Toolkit installation"
    exit 0
fi


# Reference: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
echo "Installing NVIDIA Container Toolkit"

distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
    && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
echo "Finished installing NVIDIA Container Toolkit"
echo "Restarting Docker"
sudo systemctl restart docker
echo "Testing NVIDIA Container Toolkit"
sudo docker run --rm --runtime=nvidia --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
