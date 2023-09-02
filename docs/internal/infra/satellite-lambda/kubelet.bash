#!/bin/bash

# do not mask errors in a pipeline
set -o pipefail

# treat unset variables as an error
set -o nounset

# exit script whenever it errs
set -o errexit

if [ $# -ne 8 ]; then
    echo "Usage: $0 AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION CLUSTER_NAME ASSUME_ROLE HOSTNAME_OVERRIDE NODE_LABELS NODE_INTERNAL_IP"
    exit 1
fi

export AWS_ACCESS_KEY_ID="$1"
export AWS_SECRET_ACCESS_KEY="$2"

AWS_REGION="$3"
CLUSTER_NAME="$4"
ASSUME_ROLE="$5"
HOSTNAME_OVERRIDE="$6"
NODE_LABELS="$7"
NODE_INTERNAL_IP="$8"



#######
# download kubeconfig and CA certificate from EKS cluster
DESCRIBE_CLUSTER_RESULT="/tmp/describe_cluster_result.txt"
aws eks describe-cluster \
--region=${AWS_REGION} \
--name=${CLUSTER_NAME} \
--output=text \
--query 'cluster.{certificateAuthorityData: certificateAuthority.data, endpoint: endpoint, serviceIpv4Cidr: kubernetesNetworkConfig.serviceIpv4Cidr, serviceIpv6Cidr: kubernetesNetworkConfig.serviceIpv6Cidr, clusterIpFamily: kubernetesNetworkConfig.ipFamily, outpostArn: outpostConfig.outpostArns[0], id: id}' > $DESCRIBE_CLUSTER_RESULT
# cat $DESCRIBE_CLUSTER_RESULT

B64_CLUSTER_CA=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $1}')
echo $B64_CLUSTER_CA | base64 -d > /tmp/k8s-pki-ca.crt
sudo mv /tmp/k8s-pki-ca.crt /etc/kubernetes/pki/ca.crt



#######
# create a new dummy network interface to receive proxy traffic
# do not use ENI IP address, as api server talks to primary eni first
# use the private IP of the proxy EC2 instance
# https://linuxconfig.org/configuring-virtual-network-interfaces-in-linux
ip a && ifconfig && ip link show eth0 || true
sudo modprobe dummy && sudo ip link add eth0 type dummy && ip link show eth0
sudo ifconfig eth0 hw ether C8:D7:4A:4E:47:50
sudo ip addr add $NODE_INTERNAL_IP/24 brd + dev eth0 label eth0:0 || true
sudo ip link set dev eth0 up
ip a && ifconfig && ip link show eth0

# to remove
# sudo ip addr del $NODE_INTERNAL_IP/24 brd + dev eth0 label eth0:0
# sudo ip link delete eth0 type dummy
# sudo rmmod dummy





#######
# set kubelet overcommit
# "Failed to start ContainerManager" err="[invalid kernel flag: vm/overcommit_memory, expected value: 1, actual value: 0, invalid kernel flag: kernel/panic, expected value: 10, actual value: -1, invalid kernel flag: kernel/panic_on_oops, expected value: 1, actual value: 0]"
cat << 'EOF' > /tmp/kubelet-config-overcommit.conf
vm.overcommit_memory=1
kernel.panic=10
kernel.panic_on_oops=1
EOF
sudo mv /tmp/kubelet-config-overcommit.conf /etc/sysctl.d/90-kubelet.conf
sudo sysctl -p /etc/sysctl.d/90-kubelet.conf




#######
sudo find /etc/cni/net.d/

sudo systemctl restart --no-block containerd

sudo rm -f /var/lib/kubelet/pki/*
# sudo rm -f /var/log/kubelet.log



#######
rm -f /root/.kube/config && mkdir -p /root/.kube
aws eks update-kubeconfig --region us-east-1 --name ${CLUSTER_NAME} --kubeconfig /root/.kube/config

# 12-hour (max)
# requires https://www.freedesktop.org/software/systemd/man/systemd.timer.html
ASSUME_ROLE_OUT=$(
aws sts assume-role \
--role-arn $ASSUME_ROLE \
--role-session-name test \
--duration-seconds 43200)

echo "labeling nodes with NODE_LABELS=$NODE_LABELS"
AWS_ACCESS_KEY_ID="$(echo $ASSUME_ROLE_OUT | jq -r .Credentials.AccessKeyId)" \
AWS_SECRET_ACCESS_KEY="$(echo $ASSUME_ROLE_OUT | jq -r .Credentials.SecretAccessKey)" \
AWS_SESSION_TOKEN="$(echo $ASSUME_ROLE_OUT | jq -r .Credentials.SessionToken)" \
/usr/bin/kubelet \
--config=/etc/kubernetes/kubelet/kubelet.yaml \
--kubeconfig=/root/.kube/config \
--container-runtime-endpoint=unix:///run/containerd/containerd.sock \
--image-credential-provider-config /etc/eks/image-credential-provider/config.json \
--image-credential-provider-bin-dir /etc/eks/image-credential-provider \
--node-labels="$NODE_LABELS" \
--hostname-override $HOSTNAME_OVERRIDE \
--node-ip $NODE_INTERNAL_IP 2>&1 &
bg_pid=$!



#######
sleep 10

csr_list=$(kubectl --kubeconfig /root/.kube/config get csr -o jsonpath='{.items[*].metadata.name}')
if [ -z "$csr_list" ]; then
    echo "no pending CSRs to approve"
else
    for csr in $csr_list; do
        kubectl --kubeconfig /root/.kube/config certificate approve $csr
        echo "approved CSR: $csr"
    done

    echo "all pending CSRs have been approved"
fi



#######
echo "waiting for kubelet exit code with pid $bg_pid"
wait $bg_pid
echo "SUCCESS background process has completed"
