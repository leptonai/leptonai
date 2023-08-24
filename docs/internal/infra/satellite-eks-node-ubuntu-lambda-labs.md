# Sattelite EKS node using Lambda Labs

**THIS IS EXPERIMENTAL.**

To sum, any Lambda machine can be an EKS node outside of AWS as long as it's created as a [fargate-kind node](https://github.com/leptonai/lepton/issues/2267#issuecomment-1673969397), and with host networking, we can run pods on the satellite node.

## Goals

- On-prem node running outside of AWS can be authorized to join the EKS cluster.
- The node can be stably running sending heartbeats to the EKS cluster.
- The node can run a pod(s).
- The node can run Kubernetes deployments with services, using Node IP.

## TODOs

- GPU workloads.
- Connect via VPN.
- See [GH#2663](https://github.com/leptonai/lepton/issues/2663) for more.

## Prerequisites

- Lambda Labs instance with Ubuntu 20.04 or 22.04, outside of EKS cluster VPC
- EKS cluster
  - We will modity aws-auth configmap so highly recommend against using the existing one.
  - If we modify wrong, you will be locked out of the cluster access.

`machine` CLI (helper tool to create ENI resources):

```bash
cd ${HOME}/lepton
go build -o /tmp/ma ./machine
/tmp/ma -h
cp /tmp/ma ${GOPATH}/bin/ma

ma a w
```

## Steps

### Step 1. Create/pick a cluster to create a node

Preferrably, create a new `eks-lepton` cluster for this experiment.

### Step 2. Create a Lambda Cloud instance for the satellite node

```bash
ma l i l
ma l i c \
--name gyuho-test \
--instance-type gpu_1x_a10 \
--region us-west-1 \
--ssh-key-names gyuho-test
```

### Step 3. Install dependencies in Lambda Cloud instance

```bash
# Welcome to Ubuntu 20.04.5 LTS (GNU/Linux 5.15.0-67-generic x86_64)
ssh -o "StrictHostKeyChecking no" -i ~/.lambda-labs/ssh.private.pem ubuntu@138.2.229.235

# aws, docker, containerd, runc are already installed
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/init.bash ubuntu@138.2.229.235:/tmp/init.bash
```

In the remote machine:

```bash
# ssh
vi /tmp/init.bash
sudo bash /tmp/init.bash
```

### Step 4. Set up certs for AWS Client VPN

```bash
cd /tmp
rm -rf /tmp/easy-rsa
git clone https://github.com/OpenVPN/easy-rsa.git /tmp/easy-rsa

cd /tmp/easy-rsa/easyrsa3
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa build-server-full server nopass
./easyrsa build-client-full client1.domain.tld nopass

rm -rf satellite-lambda/vpn/
mkdir -p satellite-lambda/vpn/

cd /tmp/easy-rsa/easyrsa3

cp pki/ca.crt satellite-lambda/vpn/
cp pki/private/ca.key satellite-lambda/vpn/

cp pki/issued/server.crt satellite-lambda/vpn/
cp pki/private/server.key satellite-lambda/vpn/

cp pki/issued/client1.domain.tld.crt satellite-lambda/vpn/
cp pki/private/client1.domain.tld.key satellite-lambda/vpn/

cd satellite-lambda/vpn/
aws acm import-certificate \
--certificate fileb://server.crt \
--private-key fileb://server.key \
--certificate-chain fileb://ca.crt
# arn:aws:acm:us-east-1:605454121064:certificate/d326050a-03f8-46a3-8577-a4ee563c2987

cd satellite-lambda/vpn/
aws acm import-certificate \
--certificate fileb://client1.domain.tld.crt \
--private-key fileb://client1.domain.tld.key \
--certificate-chain fileb://ca.crt
# arn:aws:acm:us-east-1:605454121064:certificate/4c7d84ff-f048-41f4-a0c7-af57b1be0ded
```

### Step 5. Create AWS Client VPN connection to access VPC

```bash
# step 5-1. create log stream for VPN connection
aws logs create-log-stream \
--region us-east-1 \
--log-group-name /aws/eks/gh61/cluster \
--log-stream-name vpn

# step 5-2. create client VPN endpoint
# https://docs.aws.amazon.com/cli/latest/reference/ec2/create-client-vpn-endpoint.html
ma a -r us-east-1 k l
ma a -r us-east-1 v g vpc-017bd15e7c79d5c0e
aws ec2 create-client-vpn-endpoint \
--region us-east-1 \
--description gh61 \
--client-cidr-block 10.0.68.0/22 \
--server-certificate-arn arn:aws:acm:us-east-1:605454121064:certificate/d326050a-03f8-46a3-8577-a4ee563c2987 \
--authentication-options Type=certificate-authentication,MutualAuthentication={ClientRootCertificateChainArn=arn:aws:acm:us-east-1:605454121064:certificate/4c7d84ff-f048-41f4-a0c7-af57b1be0ded} \
--connection-log-options Enabled=true,CloudwatchLogGroup=/aws/eks/gh61/cluster,CloudwatchLogStream=vpn \
--vpc-id vpc-017bd15e7c79d5c0e \
--vpn-port 443 \
--tag-specifications 'ResourceType=client-vpn-endpoint,Tags=[{Key=Name,Value=gh61}]' \
--split-tunnel
# cvpn-endpoint-00561e95187909400

# step 5-3. associate target private subnet
# https://docs.aws.amazon.com/cli/latest/reference/ec2/associate-client-vpn-target-network.html#
ma a -r us-east-1 k l
ma a -r us-east-1 v g vpc-017bd15e7c79d5c0e
# pick private-us-east-1a
aws ec2 associate-client-vpn-target-network \
--region us-east-1 \
--client-vpn-endpoint-id cvpn-endpoint-00561e95187909400 \
--subnet-id subnet-0d8407df7fee0a6d2

# step 5-3.
# either
#
# update default security group inbound/outbound
# make sure the applied sg has all traffic + 0.0.0.0 for inbound/outbound
#
# make sure
# EKS created security group applied to ENI that is attached to EKS Control Plane master nodes, as well as any managed workloads.
# inbound rule has the default "sg-038dc417abbbe3c1a" as inbound rule for all traffic
#
# or
#
# step 5-3. create a new sg group for VPN connection
# required for remote host to access EKS cluster endpoints
# https://docs.aws.amazon.com/cli/latest/reference/ec2/create-security-group.html
aws ec2 create-security-group \
--vpc-id vpc-017bd15e7c79d5c0e \
--description gh61-vpn-sg \
--group-name gh61-vpn-sg
# sg-0529d29fcc15ddbc5

# https://docs.aws.amazon.com/cli/latest/reference/ec2/authorize-security-group-ingress.html
# https://docs.aws.amazon.com/cli/latest/reference/ec2/authorize-security-group-egress.html
aws ec2 authorize-security-group-ingress \
--region us-east-1 \
--group-id sg-0529d29fcc15ddbc5 \
--protocol all \
--cidr 0.0.0.0/0

# EKS created security group applied to ENI that is attached to EKS Control Plane master nodes, as well as any managed workloads.
# inbound rule has inbound rule for all traffic
ma a -r us-east-1 k l
ma a -r us-east-1 v g vpc-017bd15e7c79d5c0e
# sg-0e58e5d6271b4a30d
aws ec2 authorize-security-group-ingress \
--region us-east-1 \
--group-id sg-0e58e5d6271b4a30d \
--protocol all \
--cidr 0.0.0.0/0

# step 5-4. apply security group to VPN connection
# https://docs.aws.amazon.com/cli/latest/reference/ec2/apply-security-groups-to-client-vpn-target-network.html
# pick default sg or the one you just created
aws ec2 apply-security-groups-to-client-vpn-target-network \
--region us-east-1 \
--client-vpn-endpoint-id cvpn-endpoint-00561e95187909400 \
--vpc-id vpc-017bd15e7c79d5c0e \
--security-group-ids sg-0529d29fcc15ddbc5

# step 5-5. update VPN authorization rules
# https://docs.aws.amazon.com/cli/latest/reference/ec2/authorize-client-vpn-ingress.html
aws ec2 authorize-client-vpn-ingress \
--region us-east-1 \
--client-vpn-endpoint-id cvpn-endpoint-00561e95187909400 \
--authorize-all-groups \
--target-network-cidr 10.0.0.0/16

# step 5-6. add lambda machine public IP to VPN route table for SSH traffic
# https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-working-routes.html
# https://docs.aws.amazon.com/cli/latest/reference/ec2/create-client-vpn-route.html
# "138.2.238.131" is the public IP of the lambda host
aws ec2 create-client-vpn-route \
--region us-east-1 \
--client-vpn-endpoint-id cvpn-endpoint-00561e95187909400 \
--destination-cidr-block 138.2.238.131/32 \
--target-vpc-subnet-id subnet-0d8407df7fee0a6d2
```

### Step 6. Download AWS Client VPN config file from AWS

```bash
aws ec2 export-client-vpn-client-configuration \
--client-vpn-endpoint-id cvpn-endpoint-00561e95187909400 \
--output text > satellite-lambda/vpn/downloaded-client-config.ovpn
```

Make sure to update the config file with key and cert fields:

```bash
cat satellite-lambda/vpn/client1.domain.tld.crt
cat satellite-lambda/vpn/client1.domain.tld.key
vi satellite-lambda/vpn/downloaded-client-config.ovpn
```

```text
<cert>
TODO
</cert>

<key>
TODO
</key>
```

### Step 7. Connect the remote Lambda machine to AWS Client VPN

```bash
scp -i satellite-lambda/ssh.private.pem \
satellite-lambda/vpn/downloaded-client-config.ovpn \
ubuntu@138.2.238.131:/tmp/downloaded-client-config.ovpn
ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131 "sudo mv /tmp/downloaded-client-config.ovpn /etc/downloaded-client-config.ovpn"
ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131 "tail /etc/downloaded-client-config.ovpn"

ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131

sudo vi /etc/downloaded-client-config.ovpn
tail /etc/downloaded-client-config.ovpn

# add the following to enable SSH
# we do not need if we add public IP as VPN connection route
# route-nopull
# route 138.2.238.131 255.255.255.255 net_gateway

# in remote machine
# https://docs.aws.amazon.com/pdfs/vpn/latest/clientvpn-admin/client-vpn-admin-guide.pdf
tmux new-session
tmux attach-session -t 0
sudo openvpn --config /etc/downloaded-client-config.ovpn
```

### Step 8. Check VPC access connectivity using VPN connection

```bash
# ifconfig to get the IP, or get client connection from AWS Client VPN console
# 10.0.68.34
# use this for kubelet config + kubelet flag
ifconfig
```

```bash
# connect to VPN using AWS VPN client
aws eks update-kubeconfig --region us-east-1 --name gh61
kubectl get endpoints

# both EC2 and Lambda can access cluster endpoints
NAME         ENDPOINTS                        AGE
kubernetes   10.0.16.135:443,10.0.33.58:443   4h11m
my-app       10.0.68.34:8080                  26m

# make sure you can connect to EKS cluster
curl -k https://10.0.16.135:443
curl -k https://10.0.33.58:443
```

```bash
# we can access VPC, but not from VPC to lambda
# from lambda to AWS via private IP
#
# EC2 open port 8080 with instance of cluster sg group
# Lambda can access via private IP 10.0.24.211
# but cannot access if EC2's in VPN
aws ssm start-session --region us-east-1 --target i-03b46467ba38ad90a
nc -l 8080
# from lambda remote machine
nc -vz 10.0.24.211 8080
# telnet 10.0.24.211 8080

# TODO
# CANNOT access Lambda from VPC
#
# lambda open port 8081 with instance of VPN connection sg group
ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131
nc -l 8081
# from ec2 remote machine
nc -vz 10.0.68.34 8081
# telnet 10.0.68.34 8081

# EC2 can only access via public IP
nc -vz 138.2.238.131 8081
```

### WE ARE STUCK HERE

Basically, using VPC, we can access AWS EKS VPC IPs from VPN-connected Lambda Labs hosts (e.g., connect to EC2 private IPs, EKS control plane endpoints, etc.). But, EKS control plane or EC2 instance cannot route to VPN-connected Lambda Labs hosts.

![vpc-reachability-analysis](./satellite-lambda/vpc-reachability-analysis.png)

This is because all private subnet outbound traffic to `10.0.0.0/16` are routed using the local route table, which has the following route:

![vpc-private-subnet-route-table.png](./satellite-lambda/vpc-private-subnet-route-table.png)

See the following articles for more information:

- [Client-to-client access using AWS Client VPN](https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/scenario-client-to-client.html)
- ["connection can only be initiated from the client to the EC2 instance and it wouldn't work for the connections initiated in the other direction."](https://serverfault.com/questions/964767/unable-to-ping-vpn-clients-from-target-subnet)

Without this step, kubelet exec/logs would not work...

We can still schedule pods on the satellite node, but we cannot access the pod. See below for the remaining steps.

### Step 10. Create an ENI for the satellite node

```bash
# to pick subnet ID + security group ID
ma a -r us-east-1 k l
ma a -r us-east-1 v g vpc-0776c6668008e90a9

# to create an ENI
ma a -r us-east-1 n c \
--subnet-id subnet-051a611f159253cba \
--sg-ids sg-03ed97e5202d027ed \
--name gh058-satellite-node-01 \
--description gh058-satellite-node-01

# to list ENIs
ma a -r us-east-1 n l
ma a -r us-east-1 n g eni-086d663f3201384e3
```

```text
*-----------------------*-------------------------*------------*------------*---------------------------*-----------------------*--------------------------*------------*----------------------*
|        ENI ID         |     ENI DESCRIPTION     | ENI STATUS | PRIVATE IP |        PRIVATE DNS        |        VPC ID         |        SUBNET ID         |     AZ     |         SGS          |
*-----------------------*-------------------------*------------*------------*---------------------------*-----------------------*--------------------------*------------*----------------------*
| eni-086d663f3201384e3 | gh058-satellite-node-01 | available  | 10.0.2.27  | ip-10-0-2-27.ec2.internal | vpc-0776c6668008e90a9 | subnet-051a611f159253cba | us-east-1a | sg-03ed97e5202d027ed |
*-----------------------*-------------------------*------------*------------*---------------------------*-----------------------*--------------------------*------------*----------------------*
```

```bash
ma a -r us-east-1 k n s h eni-086d663f3201384e3
# fargate-ip-10-0-2-27.us-east-1.compute.internal
```

```bash
# to delete an ENI
# ma a -r us-east-1 n d eni-086d663f3201384e3
```

### Step 11. Download EKS kubeconfig and CA certificate

```bash
ma a -r us-east-1 k l
ma a -r us-east-1 k k gh058
ma a -r us-east-1 k k gh058 -k /tmp/gh058.kubeconfig
```

```bash
aws eks update-kubeconfig --region us-east-1 --name gh058

DESCRIBE_CLUSTER_RESULT="/tmp/describe_cluster_result.txt"
aws eks describe-cluster \
--region=us-east-1 \
--name=gh058 \
--output=text \
--query 'cluster.{certificateAuthorityData: certificateAuthority.data, endpoint: endpoint, serviceIpv4Cidr: kubernetesNetworkConfig.serviceIpv4Cidr, serviceIpv6Cidr: kubernetesNetworkConfig.serviceIpv6Cidr, clusterIpFamily: kubernetesNetworkConfig.ipFamily, outpostArn: outpostConfig.outpostArns[0], id: id}' > $DESCRIBE_CLUSTER_RESULT

cat $DESCRIBE_CLUSTER_RESULT

B64_CLUSTER_CA=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $1}')
APISERVER_ENDPOINT=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $3}')
CLUSTER_ID_IN_DESCRIBE_CLUSTER_RESULT=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $4}')
CLUSTER_ID=${CLUSTER_ID_IN_DESCRIBE_CLUSTER_RESULT}
OUTPOST_ARN=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $5}')
SERVICE_IPV4_CIDR=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $6}')
SERVICE_IPV6_CIDR=$(cat $DESCRIBE_CLUSTER_RESULT | awk '{print $7}')
IP_FAMILY="ipv4"

CA_CERTIFICATE_DIRECTORY=/tmp/k8s-pki
CA_CERTIFICATE_FILE_PATH=$CA_CERTIFICATE_DIRECTORY/ca.crt
mkdir -p $CA_CERTIFICATE_DIRECTORY
# sudo mkdir -p $CA_CERTIFICATE_DIRECTORY
# sudo chown -R ubuntu $CA_CERTIFICATE_DIRECTORY
echo $B64_CLUSTER_CA | base64 -d > $CA_CERTIFICATE_FILE_PATH
cat $CA_CERTIFICATE_FILE_PATH

cat /tmp/gh058.kubeconfig
cat /tmp/k8s-pki/ca.crt
```

### Step 12. Download EKS kubeconfig, CA certificate, kubelet config, containerd config, CNI config in the satellite node

This can be done in many ways. For simplicity, we just use `scp` to copy the files.

```bash
# in remote machines
ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131

# in remote machines
sudo mkdir -p /var/lib/kubelet
sudo chown -R ubuntu /var/lib/kubelet
sudo mkdir -p /etc/kubernetes/kubelet
sudo chown -R ubuntu /etc/kubernetes/kubelet
sudo mkdir -p /etc/kubernetes/pki
sudo chown -R ubuntu /etc/kubernetes/pki
sudo chown -R ubuntu /etc/containerd
find /etc/containerd
find /opt/cni/bin
sudo mkdir -p /etc/cni/net.d
sudo chown -R ubuntu /etc/cni/net.d
sudo chown -R ubuntu /etc/sysctl.d/

# kubeconfig
scp -i satellite-lambda/ssh.private.pem /tmp/gh61.kubeconfig ubuntu@138.2.238.131:/var/lib/kubelet/kubeconfig

# CA
scp -i satellite-lambda/ssh.private.pem /tmp/k8s-pki/ca.crt ubuntu@138.2.238.131:/etc/kubernetes/pki/ca.crt

# kubelet config
scp -i satellite-lambda/ssh.private.pem \
satellite-lambda/kubelet-config.yaml \
ubuntu@138.2.238.131:/etc/kubernetes/kubelet/kubelet-config.yaml

# kubelet configuration
# without it,
# "Failed to start ContainerManager" err="[invalid kernel flag: vm/overcommit_memory, expected value: 1, actual value: 0, invalid kernel flag: kernel/panic, expected value: 10, actual value: -1, invalid kernel flag: kernel/panic_on_oops, expected value: 1, actual value: 0]"
scp -i satellite-lambda/ssh.private.pem \
satellite-lambda/kubelet-config-overcommit.conf \
ubuntu@138.2.238.131:/etc/sysctl.d/90-kubelet.conf

# containerd config
scp -i satellite-lambda/ssh.private.pem \
satellite-lambda/containerd.toml \
ubuntu@138.2.238.131:/etc/containerd/config.toml

# cni config
scp -i satellite-lambda/ssh.private.pem \
satellite-lambda/cni-host-network.conf \
ubuntu@138.2.238.131:/etc/cni/net.d/10-host-network.conf

# in remote machines
ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131

# in remote machines
cat /var/lib/kubelet/kubeconfig
cat /etc/kubernetes/pki/ca.crt
cat /etc/kubernetes/kubelet/kubelet-config.yaml
cat /etc/containerd/config.toml
cat /etc/cni/net.d/10-host-network.conf
cat /etc/sysctl.d/90-kubelet.conf

sudo sysctl -p /etc/sysctl.d/90-kubelet.conf
sudo systemctl restart containerd
# sudo systemctl status containerd
```

### Step 13. Add a new user entry to aws-auth configmap

This is required for the satellite node authorization.

```bash
aws sts get-caller-identity
# arn:aws:iam::605454121064:user/gyuho
# AIDAYZ57AXBUCE2ABSLCN

ma a -r us-east-1 k n s h eni-0545f16a4b039f0ba
# fargate-ip-10-0-15-153.us-east-1.compute.internal

ma a --region us-east-1 k a g gh61
ma a --region us-east-1 k a a \
--cluster-name gh61 \
--groups system:bootstrappers,system:nodes \
--user-name system:node:fargate-ip-10-0-15-153.us-east-1.compute.internal \
--user-id AIDAYZ57AXBUCE2ABSLCN

# kubectl -n kube-system edit configmap aws-auth
kubectl -n kube-system get configmap aws-auth -o yaml
```

```yaml
apiVersion: v1
data:
  mapRoles: |
    - rolearn: arn:aws:iam::605454121064:role/gh058-mng-role
      username: system:node:{{EC2PrivateDNSName}}
      groups:
      - system:bootstrappers
      - system:nodes
    - rolearn: ""
      username: system:node:fargate-ip-10-0-2-27.us-east-1.compute.internal
      groups:
      - system:bootstrappers
      - system:nodes
      userid: AIDAYZ57AXBUCE2ABSLCN
```

### Step 14. Set up kubelet in the satellite node

```bash
# node-ip must be the one set by client VPN or leave empty
# can't use eni private IP
# since it will
# "Failed to set some node status fields" err="failed to validate nodeIP: node IP: \"10.0.8.57\" not found in the host's network interfaces" node="fargate-ip-10-0-15-153.us-east-1.compute.internal"

# find ip
# ifconfig

# in remote machines
ssh -o "StrictHostKeyChecking no" -i satellite-lambda/ssh.private.pem ubuntu@138.2.238.131

rm -f /tmp/kubelet.sh
cat << 'EOF' > /tmp/kubelet.sh
#!/bin/bash

mkdir -p /root/.kube
rm -f /root/.kube/config

AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
aws eks update-kubeconfig --region us-east-1 --name gh61

AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
kubectl get nodes

AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
/usr/bin/kubelet --config=/etc/kubernetes/kubelet/kubelet-config.yaml --kubeconfig=/root/.kube/config --container-runtime-endpoint=unix:///run/containerd/containerd.sock --image-credential-provider-config /etc/eks/image-credential-provider/config.json --image-credential-provider-bin-dir /etc/eks/image-credential-provider --node-labels eks.amazonaws.com/compute-type=fargate --hostname-override fargate-ip-10-0-15-153.us-east-1.compute.internal --node-ip 10.0.68.34
EOF
sudo chmod +x /tmp/kubelet.sh
sudo cp /tmp/kubelet.sh /usr/bin/kubelet.sh
sudo cat /usr/bin/kubelet.sh

# to run manually
# sudo bash /usr/bin/kubelet.sh

sudo rm -f /var/log/kubelet.log
rm -f /tmp/kubelet.service
cat << 'EOF' > /tmp/kubelet.service
[Unit]
Description=kubelet

[Service]
Type=simple
TimeoutStartSec=300
Restart=always
User=root
Group=root
RestartSec=5s
LimitNOFILE=40000
ExecStart=/usr/bin/kubelet.sh
StandardOutput=append:/var/log/kubelet.log
StandardError=append:/var/log/kubelet.log

[Install]
WantedBy=multi-user.target
EOF
sudo cp /tmp/kubelet.service /etc/systemd/system/kubelet.service
cat /etc/systemd/system/kubelet.service
sudo systemctl daemon-reload
```

Successful logs:

```bash
k get nodes

NAME                                              STATUS   ROLES    AGE   VERSION
fargate-ip-10-0-2-27.us-east-1.compute.internal   Ready    <none>   39m   v1.26.7
ip-10-0-19-126.ec2.internal                       Ready    <none>   17h   v1.26.6
```

```bash
k describe node fargate-ip-10-0-2-27.us-east-1.compute.internal

Name:               fargate-ip-10-0-2-27.us-east-1.compute.internal
Roles:              <none>
Labels:             beta.kubernetes.io/arch=amd64
                    beta.kubernetes.io/os=linux
                    eks.amazonaws.com/compute-type=fargate
                    kubernetes.io/arch=amd64
                    kubernetes.io/hostname=fargate-ip-10-0-2-27.us-east-1.compute.internal
                    kubernetes.io/os=linux
Annotations:        csi.volume.kubernetes.io/nodeid: {"csi.tigera.io":"fargate-ip-10-0-2-27.us-east-1.compute.internal"}
                    node.alpha.kubernetes.io/ttl: 0
                    volumes.kubernetes.io/controller-managed-attach-detach: true
CreationTimestamp:  Sun, 20 Aug 2023 11:49:27 +0800
Taints:             <none>
Unschedulable:      false
Lease:
  HolderIdentity:  fargate-ip-10-0-2-27.us-east-1.compute.internal
  AcquireTime:     <unset>
  RenewTime:       Sun, 20 Aug 2023 12:29:32 +0800
Conditions:
  Type             Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message
  ----             ------  -----------------                 ------------------                ------                       -------
  MemoryPressure   False   Sun, 20 Aug 2023 12:24:39 +0800   Sun, 20 Aug 2023 11:49:27 +0800   KubeletHasSufficientMemory   kubelet has sufficient memory available
  DiskPressure     False   Sun, 20 Aug 2023 12:24:39 +0800   Sun, 20 Aug 2023 11:49:27 +0800   KubeletHasNoDiskPressure     kubelet has no disk pressure
  PIDPressure      False   Sun, 20 Aug 2023 12:24:39 +0800   Sun, 20 Aug 2023 11:49:27 +0800   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready            True    Sun, 20 Aug 2023 12:24:39 +0800   Sun, 20 Aug 2023 11:49:28 +0800   KubeletReady                 kubelet is posting ready status. AppArmor enabled
Addresses:
  InternalIP:  10.19.60.132
  Hostname:    fargate-ip-10-0-2-27.us-east-1.compute.internal
Capacity:
  cpu:                30
  ephemeral-storage:  1422559648Ki
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             206129480Ki
  pods:               110
Allocatable:
  cpu:                30
  ephemeral-storage:  1311030969427
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             206027080Ki
  pods:               110
System Info:
  Machine ID:                 b5daa36c5840b3b9ca449c77043f147f
  System UUID:                147cac70-c9c0-4e5b-beb5-09d9aef1a610
  Boot ID:                    cea43fb4-6fa4-4aca-b3d0-98ed9461a4c1
  Kernel Version:             5.15.0-67-generic
  OS Image:                   Ubuntu 20.04.6 LTS
  Operating System:           linux
  Architecture:               amd64
  Container Runtime Version:  containerd://1.6.22
  Kubelet Version:            v1.26.7
  Kube-Proxy Version:         v1.26.7
Non-terminated Pods:          (5 in total)
  Namespace                   Name                                                    CPU Requests  CPU Limits  Memory Requests  Memory Limits  Age
  ---------                   ----                                                    ------------  ----------  ---------------  -------------  ---
  calico-system               csi-node-driver-tm5tl                                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         100m
  default                     my-app-b97f997c4-cc798                                  0 (0%)        0 (0%)      0 (0%)           0 (0%)         80m
  default                     nginx                                                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         80m
  gpu-operator                gpu-operator-node-feature-discovery-worker-8kwj6        0 (0%)        0 (0%)      0 (0%)           0 (0%)         44m
  kube-prometheus-stack       kube-prometheus-stack-prometheus-node-exporter-w4thz    0 (0%)        0 (0%)      0 (0%)           0 (0%)         100m
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests  Limits
  --------           --------  ------
  cpu                0 (0%)    0 (0%)
  memory             0 (0%)    0 (0%)
  ephemeral-storage  0 (0%)    0 (0%)
  hugepages-1Gi      0 (0%)    0 (0%)
  hugepages-2Mi      0 (0%)    0 (0%)
Events:
  Type     Reason                   Age                  From             Message
  ----     ------                   ----                 ----             -------
  Warning  MissingClusterDNS        50m (x44 over 100m)  kubelet          kubelet does not have ClusterDNS IP configured and cannot create Pod using "ClusterFirst" policy. Falling back to "Default" policy.
  Normal   Starting                 44m                  kubelet          Starting kubelet.
  Warning  InvalidDiskCapacity      44m                  kubelet          invalid capacity 0 on image filesystem
  Normal   NodeHasSufficientMemory  44m (x2 over 44m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasSufficientMemory
  Normal   NodeHasNoDiskPressure    44m (x2 over 44m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasNoDiskPressure
  Normal   NodeHasSufficientPID     44m (x2 over 44m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasSufficientPID
  Normal   NodeAllocatableEnforced  44m                  kubelet          Updated Node Allocatable limit across pods
  Normal   NodeReady                44m                  kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeReady
  Warning  MissingClusterDNS        43m (x15 over 44m)   kubelet          kubelet does not have ClusterDNS IP configured and cannot create Pod using "ClusterFirst" policy. Falling back to "Default" policy.
  Normal   NodeHasSufficientMemory  40m (x2 over 40m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasSufficientMemory
  Normal   NodeAllocatableEnforced  40m                  kubelet          Updated Node Allocatable limit across pods
  Warning  InvalidDiskCapacity      40m                  kubelet          invalid capacity 0 on image filesystem
  Normal   Starting                 40m                  kubelet          Starting kubelet.
  Normal   NodeHasNoDiskPressure    40m (x2 over 40m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasNoDiskPressure
  Normal   NodeHasSufficientPID     40m (x2 over 40m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasSufficientPID
  Normal   NodeReady                40m                  kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeReady
  Normal   RegisteredNode           40m                  node-controller  Node fargate-ip-10-0-2-27.us-east-1.compute.internal event: Registered Node fargate-ip-10-0-2-27.us-east-1.compute.internal in Controller
  Warning  MissingClusterDNS        35m (x34 over 40m)   kubelet          kubelet does not have ClusterDNS IP configured and cannot create Pod using "ClusterFirst" policy. Falling back to "Default" policy.
  Normal   Starting                 30m                  kubelet          Starting kubelet.
  Warning  InvalidDiskCapacity      30m                  kubelet          invalid capacity 0 on image filesystem
  Normal   NodeHasSufficientMemory  30m (x2 over 30m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasSufficientMemory
  Normal   NodeHasNoDiskPressure    30m (x2 over 30m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasNoDiskPressure
  Normal   NodeHasSufficientPID     30m (x2 over 30m)    kubelet          Node fargate-ip-10-0-2-27.us-east-1.compute.internal status is now: NodeHasSufficientPID
  Normal   NodeAllocatableEnforced  30m                  kubelet          Updated Node Allocatable limit across pods
  Warning  MissingClusterDNS        33s (x173 over 30m)  kubelet          kubelet does not have ClusterDNS IP configured and cannot create Pod using "ClusterFirst" policy. Falling back to "Default" policy.
```

### Step 15. Start kubelet service to join the network

```bash
# in case it's already running
sudo systemctl stop kubelet.service
sudo systemctl disable kubelet.service
sudo systemctl enable kubelet.service

sudo rm -f /var/log/kubelet.log
sudo systemctl restart --no-block kubelet.service
# sudo systemctl status kubelet.service
sudo tail -f /var/log/kubelet.log
```

```bash
# optional: manually register with "registerNode: false"
ma a --region us-east-1 k n s a \
--cluster-name gh61 \
--eni-id eni-0545f16a4b039f0ba \
--keep=true \
--keep-interval=10s \
--taint-gpu

k get nodes
```

### Step 16. Deploy test node port app

```bash
k apply -f ./satellite-lambda/node-port-app.yaml
k apply -f ./satellite-lambda/nginx.yaml
k get po -o wide
```

- http://138.2.229.235:8080
- http://138.2.229.235

And connect to the service using the Lambda Labs instance public IP + port 8080:

![service-demo-8080](satellite-lambda/service-demo-8080.png)

![service-demo-nginx](satellite-lambda/service-demo-nginx.png)

### Step 17. Check pod logs

**THIS DOES NOT WORK...***
