#!/usr/bin/env bash

# print all executed commands to terminal
set -x

# do not mask errors in a pipeline
set -o pipefail

# treat unset variables as an error
set -o nounset

# exit script whenever it errs
set -o errexit

# makes the  default answers be used for all questions
export DEBIAN_FRONTEND=noninteractive

############################################
### Machine Architecture ###################
############################################
# https://github.com/awslabs/amazon-eks-ami/blob/master/scripts/install-worker.sh
# 'dpkg --print-architecture' to decide amd64/arm64
# 'uname -m' to decide x86_64/aarch64

MACHINE=$(uname -m)
if [ "$MACHINE" == "x86_64" ]; then
    ARCH="amd64"
elif [ "$MACHINE" == "aarch64" ]; then
    ARCH="arm64"
else
    echo "Unknown machine architecture '$MACHINE'" >&2
    exit 1
fi
echo MACHINE: $MACHINE
echo ARCH: $ARCH

# running as root, in /, check CPU/OS/host info
whoami
pwd
lscpu
cat /etc/os-release
hostnamectl

############################################
### Basic packages #########################
############################################

sudo mkdir -p /etc/systemd/system
sudo chown -R ubuntu:ubuntu /etc/systemd/system

while [ 1 ]; do
    sudo apt-get update -yq
    sudo apt-get upgrade -yq
    sudo apt-get install -yq \
    build-essential tmux git xclip htop zsh \
    jq curl wget \
    zip unzip gzip tar \
    libssl-dev \
    pkg-config lsb-release vim \
    linux-headers-$(uname -r)
    sudo apt-get clean
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;
while [ 1 ]; do
    sudo apt update
    sudo apt clean all
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

# /usr/sbin/iptables
which iptables
iptables --version

# /usr/sbin/iptables-save
which iptables-save
iptables-save --version

# /usr/sbin/iptables-restore
which iptables-restore
iptables-restore --version

/usr/bin/gcc --version
/usr/bin/c++ -v

if ! command -v lsb_release &> /dev/null
then
    echo "lsb_release could not be found"
    exit 1
fi
lsb_release --all

# sudo sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
# chsh -s /bin/zsh
# sudo chown -R ubuntu /home/ubuntu/.cache
# sudo chown -R ubuntu /home/ubuntu/.zshrc
# sudo chown -R ubuntu /home/ubuntu/.zsh_history

mkdir -p /home/ubuntu/.vim
sudo chown -R ubuntu /home/ubuntu/.vim
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x







###########################
# install vercmp utils
# https://github.com/awslabs/amazon-eks-ami/blob/master/scripts/install-worker.sh
# https://github.com/awslabs/amazon-eks-ami/tree/master/files/bin

while [ 1 ]; do
    rm -f /tmp/vercmp || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/files/bin/vercmp"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

chmod +x /tmp/vercmp
sudo mv /tmp/vercmp /usr/bin/vercmp
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x







###########################
# install time sync utils

# https://github.com/awslabs/amazon-eks-ami/tree/master/files/bin/configure-clocksource
while [ 1 ]; do
    rm -f /tmp/configure-clocksource || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/files/bin/configure-clocksource"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;
chmod +x /tmp/configure-clocksource
sudo mv /tmp/configure-clocksource /usr/bin/configure-clocksource

# https://github.com/awslabs/amazon-eks-ami/commit/056e31f8c7477e893424abce468cb32bbcd1f079#diff-049390d14bc3ea2d7882ff0f108e2802ad9b043336c5fa637e93581d9a7fdfc2
while [ 1 ]; do
    rm -f /tmp/configure-clocksource.service || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/files/configure-clocksource.service"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;
sudo mv /tmp/configure-clocksource.service /etc/systemd/system/configure-clocksource.service
sudo chown root:root /etc/systemd/system/configure-clocksource.service
systemctl daemon-reload
systemctl enable --now configure-clocksource
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# bumping up system limits
# https://github.com/awslabs/amazon-eks-ami/blob/master/scripts/install-worker.sh

echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
echo fs.inotify.max_user_instances=8192 | sudo tee -a /etc/sysctl.conf
echo vm.max_map_count=524288 | sudo tee -a /etc/sysctl.conf

# e.g.,
# "Accept error: accept tcp [::]:9650: accept4: too many open files; retrying in 1s"
sudo echo "* hard nofile 1000000" >> /etc/security/limits.conf
sudo echo "* soft nofile 1000000" >> /etc/security/limits.conf
sudo sysctl -w fs.file-max=1000000
sudo sysctl -p
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# setting up user bash profiles

cat << 'EOF' >> /home/ubuntu/.profile
HISTSIZE=1000000
HISTFILESIZE=2000000

export VISUAL=vim
export EDITOR=vim
export GPG_TTY=$(tty)

export GOPATH=/home/ubuntu/go
alias k=kubectl
export PATH=/usr/local/go/bin:/home/ubuntu/go/bin:$PATH

EOF

cat << 'EOF' >> /home/ubuntu/.bashrc
HISTSIZE=1000000
HISTFILESIZE=2000000

export VISUAL=vim
export EDITOR=vim
export GPG_TTY=$(tty)

export GOPATH=/home/ubuntu/go
alias k=kubectl
export PATH=/usr/local/go/bin:/home/ubuntu/go/bin:$PATH

EOF

export PATH=/usr/local/go/bin:/home/ubuntu/go/bin:$PATH
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x






###########################
# install go for amd64 or arm64
# https://go.dev/dl
# 'dpkg --print-architecture' to decide amd64/arm64

# sudo rm -rf /usr/local/go
# sudo curl -s --retry 70 --retry-delay 1 https://storage.googleapis.com/golang/go1.20.7.linux-$(dpkg --print-architecture).tar.gz | sudo tar -C /usr/local/ -xz
wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://go.dev/dl/go1.20.7.linux-$(dpkg --print-architecture).tar.gz"
rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go1.20.7.linux-$(dpkg --print-architecture).tar.gz

/usr/local/go/bin/go version
go version || true
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x






###########################
# install CNI plugins
# https://github.com/containernetworking/plugins
# https://github.com/awslabs/amazon-eks-ami/blob/master/scripts/install-worker.sh
# 'dpkg --print-architecture' to decide amd64/arm64

while [ 1 ]; do
    export CNI_PLUGIN_CURRENT_VERSION=$(curl -Ls --retry 70 --retry-delay 1 https://api.github.com/repos/containernetworking/plugins/releases/latest | grep 'tag_name' | cut -d'v' -f2 | cut -d'"' -f1)
    rm -f /tmp/cni-plugins-linux-$(dpkg --print-architecture)-v${CNI_PLUGIN_CURRENT_VERSION}.tgz || true;
    rm -rf /tmp/cni-plugins-linux-$(dpkg --print-architecture)-v${CNI_PLUGIN_CURRENT_VERSION} || true;
    rm -rf /tmp/cni-plugins || true;
    mkdir -p /tmp/cni-plugins
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://github.com/containernetworking/plugins/releases/download/v${CNI_PLUGIN_CURRENT_VERSION}/cni-plugins-linux-$(dpkg --print-architecture)-v${CNI_PLUGIN_CURRENT_VERSION}.tgz" -O - | tar -xzv -C /tmp/cni-plugins
    rm -f /tmp/cni-plugins-linux-$(dpkg --print-architecture)-v${CNI_PLUGIN_CURRENT_VERSION}.tgz || true;
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

ls -lah /tmp/cni-plugins
chmod +x /tmp/cni-plugins/*

sudo mkdir -p /opt/cni/bin
sudo mv /tmp/cni-plugins/* /opt/cni/bin/
rm -rf /tmp/cni-plugins

sudo find /opt/cni/bin/
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# install ECR credential helper
# https://github.com/awslabs/amazon-ecr-credential-helper

which docker-credential-ecr-login || true
docker-credential-ecr-login version || true

while [ 1 ]; do
    export ECR_CREDENTIAL_HELPER_CURRENT_VERSION=$(curl -Ls --retry 70 --retry-delay 1 https://api.github.com/repos/awslabs/amazon-ecr-credential-helper/releases/latest | grep 'tag_name' | cut -d'v' -f2 | cut -d'"' -f1)
    rm -f /tmp/aws-iam-authenticator_${ECR_CREDENTIAL_HELPER_CURRENT_VERSION}_linux_$(dpkg --print-architecture) || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://amazon-ecr-credential-helper-releases.s3.us-east-2.amazonaws.com/${ECR_CREDENTIAL_HELPER_CURRENT_VERSION}/linux-$(dpkg --print-architecture)/docker-credential-ecr-login"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

chmod +x /tmp/docker-credential-ecr-login
sudo mv /tmp/docker-credential-ecr-login /usr/bin/docker-credential-ecr-login

# /usr/bin/docker-credential-ecr-login
which docker-credential-ecr-login
docker-credential-ecr-login version
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# install ecr-credential-provider
# https://github.com/kubernetes/cloud-provider-aws/tree/master/cmd/ecr-credential-provider
# https://github.com/kubernetes/cloud-provider-aws/releases
# https://github.com/awslabs/amazon-eks-ami/blob/master/scripts/install-worker.sh

if ! command -v go &> /dev/null
then
    echo "go could not be found"
    exit 1
fi

while [ 1 ]; do
    HOME=/home/ubuntu GOPATH=/home/ubuntu/go /usr/local/go/bin/go install -v k8s.io/cloud-provider-aws/cmd/ecr-credential-provider@v1.27.1
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

which ecr-credential-provider
chmod +x /home/ubuntu/go/bin/ecr-credential-provider
sudo cp -v /home/ubuntu/go/bin/ecr-credential-provider /usr/bin/ecr-credential-provider

# /usr/bin/ecr-credential-provider
which ecr-credential-provider

# TODO: this blocks
# ecr-credential-provider --help

sudo mkdir -p /etc/eks
sudo mkdir -p /etc/eks/image-credential-provider

sudo cp -v /home/ubuntu/go/bin/ecr-credential-provider /etc/eks/image-credential-provider/ecr-credential-provider

while [ 1 ]; do
    rm -f /tmp/ecr-credential-provider-config.json || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/files/ecr-credential-provider-config.json"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

chmod +x /tmp/ecr-credential-provider-config.json
sudo mv /tmp/ecr-credential-provider-config.json /etc/eks/image-credential-provider/config.json

sudo chown -R root:root /etc/eks
sudo chown -R ubuntu:ubuntu /etc/eks
find /etc/eks
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# install kubelet
# https://kubernetes.io/releases/
# https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
# 'dpkg --print-architecture' to decide amd64/arm64

while [ 1 ]; do
    export K8S_CURRENT_VERSION=$(curl -L -s --retry 70 --retry-delay 1 https://dl.k8s.io/release/stable.txt)
    # overwrite with 1.26
    export K8S_CURRENT_VERSION="v1.26.7"

    rm -f /tmp/kubelet || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://dl.k8s.io/release/${K8S_CURRENT_VERSION}/bin/linux/$(dpkg --print-architecture)/kubelet"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

chmod +x /tmp/kubelet
sudo mv /tmp/kubelet /usr/bin/kubelet
rm -f /tmp/kubelet

# /usr/bin/kubelet
which kubelet
kubelet --version
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# install kubectl
# https://kubernetes.io/releases/
# https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/
# 'dpkg --print-architecture' to decide amd64/arm64

while [ 1 ]; do
    export K8S_CURRENT_VERSION=$(curl -L -s --retry 70 --retry-delay 1 https://dl.k8s.io/release/stable.txt)
    # overwrite with 1.26
    export K8S_CURRENT_VERSION="v1.26.7"

    rm -f /tmp/kubectl || true;
    wget --quiet --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 --tries=70 --directory-prefix=/tmp/ --continue "https://dl.k8s.io/release/${K8S_CURRENT_VERSION}/bin/linux/$(dpkg --print-architecture)/kubectl"
    if [ $? = 0 ]; then break; fi; # check return value, break if successful (0)
    sleep 2s;
done;

chmod +x /tmp/kubectl
sudo mv /tmp/kubectl /usr/bin/kubectl
rm -f /tmp/kubectl

# /usr/bin/kubectl
which kubectl
kubectl version --client=true
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x




###########################
# USER-DEFINED POST INIT SCRIPT
echo DONE###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x





###########################
# clean up packages

sudo apt clean
sudo apt-get clean
###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x




###########################
# INIT SCRIPT COMPLETE
echo "INIT SCRIPT COMPLETE"

###########################
set +x
echo ""
echo ""
echo ""
echo ""
echo ""
set -x




