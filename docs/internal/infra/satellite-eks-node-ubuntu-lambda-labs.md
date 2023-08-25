# Sattelite EKS node using Lambda Labs

**THIS IS EXPERIMENTAL AND INTENTIONALLY NOT AUTOMATED.**

To sum, any Lambda machine can be an EKS node outside of AWS as long as it's created as a [fargate-kind node](https://github.com/leptonai/lepton/issues/2267#issuecomment-1673969397), and with host networking, we can run pods on the satellite node. And with extra steps, `kubectl logs` and `exec` works.

## Goals

- On-prem node running outside of AWS can be authorized to join the EKS cluster.
- The node can be stably running sending heartbeats to the EKS cluster.
- The node can run a pod(s).
- The node can run Kubernetes deployments with services, using Node IP.
- kubelet logs and exec work.

## Non-goals

Connecting via VPN does not work due to limitations in AWS Client VPN -- see [NOTES: AWS Client VPN](#notes-aws-client-vpn).

Thus, requires us to set up SSL passthrough proxy.

## TODOs

- GPU workloads.
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

We need to install kubelet, containerd, and CNI components.

Note that Lambda Cloud instance already has `aws`, `docker`, `containerd`, `runc` installed.

Unless needed, just use the one the Lambda Cloud machine already has.

```bash
# Welcome to Ubuntu 20.04.5 LTS (GNU/Linux 5.15.0-67-generic x86_64)
ssh -o "StrictHostKeyChecking no" -i ~/.lambda-labs/ssh.private.pem ubuntu@138.2.238.131

# aws, docker, containerd, runc are already installed
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/init.bash ubuntu@138.2.238.131:/tmp/init.bash
```

In the remote machine:

```bash
# ssh
vi /tmp/init.bash
sudo bash /tmp/init.bash
```

### Step 4. Create an ENI for the satellite node

- Most tricky part, and EKS- and satellite-node-specific
- NOT officially documented and discovered by some reverse engineering (see [source](https://github.com/leptonai/lepton/issues/2267#issuecomment-1673969397))
- Only required for the satellite node authorization

```bash
# to pick subnet ID + security group ID
ma a -r us-east-1 k l
ma a -r us-east-1 v g vpc-054e3e3d03ad1254c

# to create an ENI
# pick private subnet
# pick "Secondary EKS cluster security group to allow traffic from/to nodes" sg
ma a -r us-east-1 n c \
--subnet-id subnet-005ea515bb30d0da2 \
--sg-ids sg-0a69102d3a1400efa \
--name gh62-satellite-node-01 \
--description gh62-satellite-node-01

# to list ENIs
ma a -r us-east-1 n l
ma a -r us-east-1 n g eni-0ae8356ec326d98e5
```

```text
*-----------------------*------------------------*------------*-------------*-----------------------------*-----------------------*--------------------------*------------*----------------------*
|        ENI ID         |    ENI DESCRIPTION     | ENI STATUS | PRIVATE IP  |         PRIVATE DNS         |        VPC ID         |        SUBNET ID         |     AZ     |         SGS          |
*-----------------------*------------------------*------------*-------------*-----------------------------*-----------------------*--------------------------*------------*----------------------*
| eni-0ae8356ec326d98e5 | gh62-satellite-node-01 | available  | 10.0.14.170 | ip-10-0-14-170.ec2.internal | vpc-054e3e3d03ad1254c | subnet-005ea515bb30d0da2 | us-east-1a | sg-0a69102d3a1400efa |
*-----------------------*------------------------*------------*-------------*-----------------------------*-----------------------*--------------------------*------------*----------------------*
```

And this fargate hostname is required for later node registration:

```bash
ma a -r us-east-1 k n s h eni-0ae8356ec326d98e5
# fargate-ip-10-0-14-170.us-east-1.compute.internal
```

Why `fargate-`? We don't know why. We just know this is required by EKS.

```bash
# to delete an ENI
# ma a -r us-east-1 n d eni-0ae8356ec326d98e5
```

### Step 5. Download EKS kubeconfig and CA certificate

This is required for the satellite node authentication using the CA from the EKS control plane.

```bash
# aws eks update-kubeconfig --region us-east-1 --name gh62
# ma a -r us-east-1 k k gh62
ma a -r us-east-1 k k gh62 -k /tmp/gh62.kubeconfig
cp /tmp/gh62.kubeconfig /Users/leegyuho/.kube/config
kubectl get nodes
```

```bash
DESCRIBE_CLUSTER_RESULT="/tmp/describe_cluster_result.txt"
aws eks describe-cluster \
--region=us-east-1 \
--name=gh62 \
--output=text \
--query 'cluster.{certificateAuthorityData: certificateAuthority.data, endpoint: endpoint, serviceIpv4Cidr: kubernetesNetworkConfig.serviceIpv4Cidr, serviceIpv6Cidr: kubernetesNetworkConfig.serviceIpv6Cidr, clusterIpFamily: kubernetesNetworkConfig.ipFamily, outpostArn: outpostConfig.outpostArns[0], id: id}' > $DESCRIBE_CLUSTER_RESULT
# cat $DESCRIBE_CLUSTER_RESULT

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

cat /tmp/gh62.kubeconfig
cat /tmp/k8s-pki/ca.crt
```

### Step 6. Download EKS kubeconfig, CA certificate, kubelet config, containerd config, CNI config in the satellite node

This can be done in many ways, and will be automated in the future.

For simplicity, we just use `scp` to copy the files:

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
```

```bash
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

### Step 7. Add a new user entry to aws-auth configmap

This is required for the satellite node authorization.

*Option 1.* Just use the AWS IAM user credential for kubelet.

Pros: The user credential never expires, so much simpler.

Cons: The kubelet originated CSRs are not signed by the EKS control plane approver. Which means, `kubelet logs` and `kubectl exec` will not work.

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
    - rolearn: arn:aws:iam::605454121064:role/gh62-mng-role
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

*Option 2.* Use the AWS IAM role and session token for kubelet.

Pros: The kubelet originated CSRs can be signed by the EKS control plane approver. Which means, `kubelet logs` and `kubectl exec` will work.

Cons: The max IAM role session timeout is 4-hour, so we either need to refresh the token every 4-hour, or use IAM Roles Anywhere (to be discussed later).

```bash

```yaml
apiVersion: v1
data:
  mapRoles: |
    - rolearn: arn:aws:iam::605454121064:role/gh62-mng-role
      username: system:node:{{EC2PrivateDNSName}}
      groups:
      - system:bootstrappers
      - system:nodes
    - rolearn: arn:aws:iam::605454121064:role/gh62-satellite
      username: system:node:fargate-ip-10-0-14-170.us-east-1.compute.internal
      groups:
      - system:bootstrappers
      - system:nodes
```

We will use the role to authorize the satellite node.

Step 1. Just create an empty, separate IAM role.

Step 2. Update the trusted entity to include the user (required for assuming the role):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "EKSNodeAssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        },
        {
            "Effect": "Allow",
            "Principal": { "AWS": "arn:aws:iam::605454121064:user/gyuho" },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

Step 3. Add this role to the aws-auth configmap:

```bash
ma a --region us-east-1 k a g gh62
ma a --region us-east-1 k a a \
--cluster-name gh62 \
--groups system:bootstrappers,system:nodes \
--user-name system:node:fargate-ip-10-0-14-170.us-east-1.compute.internal \
--role-arn arn:aws:iam::605454121064:role/gh62-satellite
```

And this role can be assumed with:

```bash
aws sts assume-role \
--role-arn arn:aws:iam::605454121064:role/gh62-satellite \
--role-session-name test
```

See the following steps for further instructions.

### Step 8. Set up passthrough proxy for apiserver to kubelet traffic

Whether using VPN or not, the traffic from kubelet to kube-apiserver works fine. But the traffic from kube-apiserver to kubelet does not work due to the node IP being set outside of the cluster VPC CIDR. Note that kubelet does not allow setting arbitrary node IP, unless it's one of the IPs in the host network interfaces.

That is, in order for us to support `kubectl exec` and `logs`, we need to support kube-apiserver to kubelet traffic. And to correctly route traffic from kube-apiserver to kubelet, we need to set up a passthrough proxy to the actual lambda node public IP.

Without automation, for now, just follow the steps below:

Step 1. Create a new EC2 instance within the same VPC as the EKS cluster.

Step 2. Set up a passthrough proxy in the EC2 instance. Either use IP tables, Nginx, or simple Go proxy.

Note that you don't even need to verify TLS certs. Just relay the packets from apiserver to the Lambda Cloud public IP.

```go
package main

import (
	"fmt"
	"io"
	"net"
)

func main() {
	localPort := 10250
	remoteIP := "138.2.238.131"
	remotePort := 10250

	forward(localPort, remoteIP, remotePort)
}

func forward(localPort int, remoteIP string, remotePort int) {
	localAddr := fmt.Sprintf("0.0.0.0:%d", localPort)
	remoteAddr := fmt.Sprintf("%s:%d", remoteIP, remotePort)

	// Listen for incoming packets locally
	ln, err := net.Listen("tcp", localAddr)
	if err != nil {
		panic(err)
	}
	defer ln.Close()

	fmt.Printf("Listening %q\n", localAddr)

	for {
		localConn, err := ln.Accept()
		if err != nil {
			panic(err)
		}
		fmt.Println("local conn:", localConn.LocalAddr().String())

		// Connect to remote target
		fmt.Println("connecting to", remoteAddr)
		remoteConn, err := net.Dial("tcp", remoteAddr)

		// tlsConfig := &tls.Config{
		// 	InsecureSkipVerify: true,
		// }
		// remoteConn, err := tls.Dial("tcp", remoteAddr, tlsConfig)
		if err != nil {
			localConn.Close()
			fmt.Println("Failed to connect to remote:", err)
			continue
		}

		// Forward data bidirectionally
		go func() {
			n, err := io.Copy(localConn, remoteConn)
			if err != nil {
				fmt.Println("Local to remote copy error:", err)
				return
			}

			fmt.Println("remote -> local:", n)

			localConn.Close()
			remoteConn.Close()
		}()

		go func() {
			n, err := io.Copy(remoteConn, localConn)
			if err != nil {
				fmt.Println("Remote to local copy error:", err)
				return
			}

			fmt.Println("local -> remote:", n)

			localConn.Close()
			remoteConn.Close()
		}()
	}
}
```

### Step 9. Set up a dummy network interface in the satellite node

Once the apiserver traffic is routed to the satellite Lambda Cloud node, we need to set up a dummy network interface in the satellite node, so that the kubelet can receive the apiserve traffic.

Step 1. Open the kubelet port `:10250` in the Lambda Cloud firewall.

Step 2. Get the private IP of the proxy EC2 instance. This is because apiserver can only reach the EC2 private IP, and we will advertise/register the satellite node with that IP to send the apiserver traffic to the proxy server.

Step 3. Set up a dummy network interface in the satellite node (see [link](https://linuxconfig.org/configuring-virtual-network-interfaces-in-linux)), to listen to the proxied apiserver traffic. Note that `10.0.2.233` here is the EC2 proxy server instance private IP.

```bash
ip link show eth0
ip a
ifconfig

sudo modprobe dummy
sudo ip link add eth0 type dummy
ip link show eth0

# give the interface a random MAC address
sudo ifconfig eth0 hw ether C8:D7:4A:4E:47:50

# add an alias to the interface and configure an it with an IP address
sudo ip addr add 10.0.2.233/24 brd + dev eth0 label eth0:0

# put the interface up
sudo ip link set dev eth0 up
```

```bash
# check the interface
ifconfig
```

```text
enp5s0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 10.19.62.58  netmask 255.255.240.0  broadcast 10.19.63.255
        inet6 fe80::17ff:fe02:115c  prefixlen 64  scopeid 0x20<link>
        ether 02:00:17:02:11:5c  txqueuelen 1000  (Ethernet)
        RX packets 1116003  bytes 1188644758 (1.1 GB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 449437  bytes 61468157 (61.4 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

eth0: flags=195<UP,BROADCAST,RUNNING,NOARP>  mtu 1500
        inet6 fe80::cad7:4aff:fe4e:4750  prefixlen 64  scopeid 0x20<link>
        ether c8:d7:4a:4e:47:50  txqueuelen 1000  (Ethernet)
        RX packets 0  bytes 0 (0.0 B)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 23  bytes 1610 (1.6 KB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

eth0:0: flags=195<UP,BROADCAST,RUNNING,NOARP>  mtu 1500
        inet 10.0.2.233  netmask 255.255.255.0  broadcast 10.0.2.255
        ether c8:d7:4a:4e:47:50  txqueuelen 1000  (Ethernet)

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1000  (Local Loopback)
        RX packets 110279  bytes 18306613 (18.3 MB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 110279  bytes 18306613 (18.3 MB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
```

### Step 10. Set up kubelet in the satellite node

Now we need to set up a kubelet process (use systemd service) to start the actual node.

Note two things here:

- We are assuming the new satellite IAM role to authenticate and authorize the node.
  - We are passing the assumed IAM credential token to the kubelet.
  - `hostname-override` must be the same as the one set in aws-auth configmap.
- We are setting the `--node-ip` to the proxy EC2 instance private IP, which will be advertised to the EKS cluster apiserver, so it knows to send the traffic to the proxy.

```bash
printf "AWS_ACCESS_KEY_ID=\"%s\" \\
AWS_SECRET_ACCESS_KEY=\"%s\" \\
AWS_SESSION_TOKEN=\"%s\" \\
" \
$(AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
aws sts assume-role \
--role-arn arn:aws:iam::605454121064:role/gh62-satellite \
--role-session-name test \
--duration-seconds 14400 \
--query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
--output text)
```

```bash
rm -f /tmp/kubelet.sh
cat << 'EOF' > /tmp/kubelet.sh
#!/bin/bash

mkdir -p /root/.kube
rm -f /root/.kube/config

AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
aws eks update-kubeconfig --region us-east-1 --name gh62

AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
kubectl get nodes

AWS_ACCESS_KEY_ID="..." \
AWS_SECRET_ACCESS_KEY="..." \
AWS_SESSION_TOKEN="..." \
/usr/bin/kubelet \
--config=/etc/kubernetes/kubelet/kubelet-config.yaml \
--kubeconfig=/root/.kube/config \
--container-runtime-endpoint=unix:///run/containerd/containerd.sock \
--image-credential-provider-config /etc/eks/image-credential-provider/config.json \
--image-credential-provider-bin-dir /etc/eks/image-credential-provider \
--node-labels eks.amazonaws.com/compute-type=fargate \
--hostname-override fargate-ip-10-0-14-170.us-east-1.compute.internal \
--node-ip 10.0.2.233

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

### Step 11. Start kubelet service to join the network

```bash
sudo systemctl stop kubelet.service
sudo systemctl disable kubelet.service

sudo rm -f /var/lib/kubelet/pki/*
sudo rm -f /var/log/kubelet.log
sudo systemctl enable kubelet.service
sudo systemctl restart --no-block kubelet.service
# sudo systemctl status kubelet.service
sudo tail -f /var/log/kubelet.log
```

### Step 12. Deploy test node port app

```bash
k apply -f ./satellite-lambda/node-port-app.yaml
k apply -f ./satellite-lambda/nginx.yaml
k get po -o wide
```

- http://138.2.238.131:8080
- http://138.2.238.131

And connect to the service using the Lambda Labs instance public IP + port 8080:

![service-demo-8080](satellite-lambda/service-demo-8080.png)

![service-demo-nginx](satellite-lambda/service-demo-nginx.png)

### Step 13. Check nodes and pods

Successful output:

```bash
k get nodes

NAME                                                STATUS   ROLES    AGE   VERSION
fargate-ip-10-0-14-170.us-east-1.compute.internal   Ready    <none>   74m   v1.26.7
ip-10-0-31-11.ec2.internal                          Ready    <none>   19h   v1.26.6
ip-10-0-35-215.ec2.internal                         Ready    <none>   20h   v1.26.6
```

```bash
kubectl describe node fargate-ip-10-0-14-170.us-east-1.compute.internal

Name:               fargate-ip-10-0-14-170.us-east-1.compute.internal
Roles:              <none>
Labels:             beta.kubernetes.io/arch=amd64
                    beta.kubernetes.io/os=linux
                    eks.amazonaws.com/compute-type=fargate
                    kubernetes.io/arch=amd64
                    kubernetes.io/hostname=fargate-ip-10-0-14-170.us-east-1.compute.internal
                    kubernetes.io/os=linux
Annotations:        csi.volume.kubernetes.io/nodeid: {"csi.tigera.io":"fargate-ip-10-0-14-170.us-east-1.compute.internal"}
                    node.alpha.kubernetes.io/ttl: 0
                    volumes.kubernetes.io/controller-managed-attach-detach: true
CreationTimestamp:  Fri, 25 Aug 2023 12:45:19 +0800
Taints:             lepton.io/provider=lambda:NoSchedule
                    nvidia.com/gpu:NoSchedule
Unschedulable:      false
Lease:
  HolderIdentity:  fargate-ip-10-0-14-170.us-east-1.compute.internal
  AcquireTime:     <unset>
  RenewTime:       Fri, 25 Aug 2023 13:59:55 +0800
Conditions:
  Type             Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message
  ----             ------  -----------------                 ------------------                ------                       -------
  MemoryPressure   False   Fri, 25 Aug 2023 13:57:19 +0800   Fri, 25 Aug 2023 12:45:19 +0800   KubeletHasSufficientMemory   kubelet has sufficient memory available
  DiskPressure     False   Fri, 25 Aug 2023 13:57:19 +0800   Fri, 25 Aug 2023 12:45:19 +0800   KubeletHasNoDiskPressure     kubelet has no disk pressure
  PIDPressure      False   Fri, 25 Aug 2023 13:57:19 +0800   Fri, 25 Aug 2023 12:45:19 +0800   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready            True    Fri, 25 Aug 2023 13:57:19 +0800   Fri, 25 Aug 2023 12:45:20 +0800   KubeletReady                 kubelet is posting ready status. AppArmor enabled
Addresses:
  InternalIP:  10.0.2.233
  Hostname:    fargate-ip-10-0-14-170.us-east-1.compute.internal
Capacity:
  cpu:                30
  ephemeral-storage:  1422559648Ki
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             206129488Ki
  pods:               110
Allocatable:
  cpu:                30
  ephemeral-storage:  1311030969427
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             206027088Ki
  pods:               110
System Info:
  Machine ID:                 30121a4ad8a27fa8f33033798287ee07
  System UUID:                233ca4a1-f1dd-4d92-89f2-378e02de01f8
  Boot ID:                    cbae0eab-c117-4829-a5d8-04809e203e9d
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
  calico-system               calico-typha-59d588595f-drk4l                           0 (0%)        0 (0%)      0 (0%)           0 (0%)         74m
  calico-system               csi-node-driver-dmqn9                                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         13h
  default                     my-app-6d788947d8-lpx9k                                 0 (0%)        0 (0%)      0 (0%)           0 (0%)         13h
  default                     nginx                                                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         70m
  kube-prometheus-stack       kube-prometheus-stack-prometheus-node-exporter-zzqmd    0 (0%)        0 (0%)      0 (0%)           0 (0%)         13h
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
  Type     Reason             Age                  From     Message
  ----     ------             ----                 ----     -------
  Warning  MissingClusterDNS  4m5s (x58 over 74m)  kubelet  kubelet does not have ClusterDNS IP configured and cannot create Pod using "ClusterFirst" policy. Falling back to "Default" policy.
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

### Step 14. Manually approve CSRs

Note that in order for kubectl exec and logs to work, the kubelet originated CSRs must be approved and issued.

The default eks-approver and signer approves and signs based on the hostname, which does not work for our satellite node objects. Thus, we need to approve manually. And then the signed certs will be issued automatically, so long as the node authorizes with the correct credential (the one in aws-auth configmap). Which is why we cannot use the IAM user for the node authorization.

```bash
# to get the current pending CSRs
k get csr

csr-d682r   34s     kubernetes.io/kubelet-serving   system:node:fargate-ip-10-0-14-170.us-east-1.compute.internal   <none>              Pending
```

```bash
# to manually approve
k certificate approve csr-d682r
```

Shortly, the **eks-signer will issue certs for the approved CSR:**

```bash
csr-d682r   65s     kubernetes.io/kubelet-serving   system:node:fargate-ip-10-0-14-170.us-east-1.compute.internal   <none>              Approved,Issued
```

You can inspect the certificate with:

```bash
k get csr csr-d682r -o yaml
```

```yaml
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  creationTimestamp: "2023-08-25T04:45:20Z"
  generateName: csr-
  name: csr-d682r
  resourceVersion: "503058"
  uid: 4a84b570-c0a1-4f13-8c4d-8f1ebf6f6a7c
spec:
  extra:
    accessKeyId:
    - ASIAYZ57AXBUL6JBOSW6
    arn:
    - arn:aws:sts::605454121064:assumed-role/gh62-satellite/test
    canonicalArn:
    - arn:aws:iam::605454121064:role/gh62-satellite
    principalId:
    - AROAYZ57AXBUAFZAZQGKU
    sessionName:
    - test
  groups:
  - system:bootstrappers
  - system:nodes
  - system:authenticated
  request: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURSBSRVFVRVNULS0tLS0KTUlJQmJ6Q0NBUllDQVFBd1h6RVZNQk1HQTFVRUNoTU1jM2x6ZEdWdE9tNXZaR1Z6TVVZd1JBWURWUVFERXoxegplWE4wWlcwNmJtOWtaVHBtWVhKbllYUmxMV2x3TFRFd0xUQXRNVFF0TVRjd0xuVnpMV1ZoYzNRdE1TNWpiMjF3CmRYUmxMbWx1ZEdWeWJtRnNNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVhZm13blN6R3hqNlYKY21KTWdvN1kzc1kzZW16cXc1dkVrSFJBMHpxODVXemM0WlVlS0U1T0pmbjZtVHB0cW10ZUFpS0FRa3VJL3RYKworMU5RSWU5Qm5LQlZNRk1HQ1NxR1NJYjNEUUVKRGpGR01FUXdRZ1lEVlIwUkJEc3dPWUl4Wm1GeVoyRjBaUzFwCmNDMHhNQzB3TFRFMExURTNNQzUxY3kxbFlYTjBMVEV1WTI5dGNIVjBaUzVwYm5SbGNtNWhiSWNFQ2dBQzZUQUsKQmdncWhrak9QUVFEQWdOSEFEQkVBaUJuQTN0NTZ0VnlnSXBQRzlwc0Mwb3FhN1pGMU5tNVRUOHE0WkxKanJ6NQpVQUlnYk9MNTN6amg1bTZlUVlYaDFRdlF3QXVieFI2WnorL1dkcjZHUFJhY0FtVT0KLS0tLS1FTkQgQ0VSVElGSUNBVEUgUkVRVUVTVC0tLS0tCg==
  signerName: kubernetes.io/kubelet-serving
  uid: aws-iam-authenticator:605454121064:AROAYZ57AXBUAFZAZQGKU
  usages:
  - digital signature
  - key encipherment
  - server auth
  username: system:node:fargate-ip-10-0-14-170.us-east-1.compute.internal
status:
  certificate: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM4akNDQWRxZ0F3SUJBZ0lVTGlvWWdzRGJwOXUvbTFMM1p5NUJmUTFwNVp3d0RRWUpLb1pJaHZjTkFRRUwKQlFBd0ZURVRNQkVHQTFVRUF4TUthM1ZpWlhKdVpYUmxjekFlRncweU16QTRNalV3TkRReE1EQmFGdzB5TkRBNApNalF3TkRReE1EQmFNRjh4RlRBVEJnTlZCQW9UREhONWMzUmxiVHB1YjJSbGN6RkdNRVFHQTFVRUF4TTljM2x6CmRHVnRPbTV2WkdVNlptRnlaMkYwWlMxcGNDMHhNQzB3TFRFMExURTNNQzUxY3kxbFlYTjBMVEV1WTI5dGNIVjAKWlM1cGJuUmxjbTVoYkRCWk1CTUdCeXFHU000OUFnRUdDQ3FHU000OUF3RUhBMElBQkduNXNKMHN4c1krbFhKaQpUSUtPMk43R04zcHM2c09ieEpCMFFOTTZ2T1ZzM09HVkhpaE9UaVg1K3BrNmJhcHJYZ0lpZ0VKTGlQN1YvdnRUClVDSHZRWnlqZ2Jvd2diY3dEZ1lEVlIwUEFRSC9CQVFEQWdXZ01CTUdBMVVkSlFRTU1Bb0dDQ3NHQVFVRkJ3TUIKTUF3R0ExVWRFd0VCL3dRQ01BQXdIUVlEVlIwT0JCWUVGR1pHNk1uZHl0eUFsQlZDdEtiSU4rOXJHU2QrTUI4RwpBMVVkSXdRWU1CYUFGR1ljNU8vdG5sUDhHK01veEh2VWtMVHdiSGJzTUVJR0ExVWRFUVE3TURtQ01XWmhjbWRoCmRHVXRhWEF0TVRBdE1DMHhOQzB4TnpBdWRYTXRaV0Z6ZEMweExtTnZiWEIxZEdVdWFXNTBaWEp1WVd5SEJBb0EKQXVrd0RRWUpLb1pJaHZjTkFRRUxCUUFEZ2dFQkFLRUM1blB0bTBicHY3TVJTYUxlKzBIcGZGZlk3N24xQ0F2dwpMUG9yZHZZYWhkNFlpQ2krazdPTFhua2hMQ2VGVU5vVXg0WXYwMllnUWxuSXZFMGo1WENxYlFLMDN6bThDaEVaCkZWRkZXTE05eWpKTmUwTkZReU44bnlKQjh1ZFc1Y29yenJVck4vYzNNTVVLbTNsK2JHOXNYa3lFK3lsSzNrUXMKZnpSa0huZzVTYmRMcU9UVHd2dGd0Z2tubHNwOUdnTER6blhTNzNSajRZd1hmUnBqRGU2VERjczNKbWJYQ0hINApUWHpBVjdZaGEvamdpc2luSVZUVkgzUS93SjVXRmsyWDJWRGUwdGdkTm5TZ3JqNG1QTm0yNVlZVWNvelZZaUp6Cm4xQlRGSzg3dU0ybU9sOTJRaXNpTHZoYkc2RVozdE9JY2xrUVEyS25wL0J4Qi9zUUxEcz0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=
  conditions:
  - lastTransitionTime: "2023-08-25T04:46:22Z"
    lastUpdateTime: "2023-08-25T04:46:22Z"
    message: This CSR was approved by kubectl certificate approve.
    reason: KubectlApprove
    status: "True"
    type: Approved
```

```bash
# status.certificate field
echo ... | base64 -d
openssl x509 -in ...cert -text -noout
```

You can see the CSR correctly includes the IP in the cert SAN field:

```text
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number:
            59:67:64:e6:95:18:ef:31:a5:a4:2d:97:08:34:82:bd:b8:fc:e0:03
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: CN = kubernetes
        Validity
            Not Before: Aug 25 04:53:00 2023 GMT
            Not After : Aug 24 04:53:00 2024 GMT
        Subject: O = system:nodes, CN = system:node:fargate-ip-10-0-14-170.us-east-1.compute.internal
        Subject Public Key Info:
            Public Key Algorithm: id-ecPublicKey
                Public-Key: (256 bit)
                pub:
                    04:81:33:dc:f4:ce:86:df:c0:c3:09:c4:05:30:0f:
                    dc:6f:9a:56:c9:bb:ab:d1:ea:3d:84:d4:fb:62:f6:
                    10:39:a2:3d:e9:61:aa:9a:8a:eb:ba:0f:a6:f0:79:
                    b5:9f:0f:6f:d0:70:ba:32:06:69:fc:81:18:0d:b7:
                    65:2f:67:63:bc
                ASN1 OID: prime256v1
                NIST CURVE: P-256
        X509v3 extensions:
            X509v3 Key Usage: critical
                Digital Signature, Key Encipherment
            X509v3 Extended Key Usage:
                TLS Web Server Authentication
            X509v3 Basic Constraints: critical
                CA:FALSE
            X509v3 Subject Key Identifier:
                AC:B0:BD:6B:6A:75:7F:FF:CB:D2:38:12:EF:E0:F6:15:F2:4A:78:A1
            X509v3 Authority Key Identifier:
                66:1C:E4:EF:ED:9E:53:FC:1B:E3:28:C4:7B:D4:90:B4:F0:6C:76:EC
            X509v3 Subject Alternative Name:
                DNS:fargate-ip-10-0-14-170.us-east-1.compute.internal, IP Address:10.0.2.233
    Signature Algorithm: sha256WithRSAEncryption
```

### Step 15. Check pod logs and exec

```bash
k get po -o wide

NAME                      READY   STATUS    RESTARTS   AGE   IP           NODE                                                NOMINATED NODE   READINESS GATES
my-app-6d788947d8-lpx9k   1/1     Running   0          13h   10.0.2.233   fargate-ip-10-0-14-170.us-east-1.compute.internal   <none>           <none>
nginx                     1/1     Running   0          72m   10.0.2.233   fargate-ip-10-0-14-170.us-east-1.compute.internal   <none>           <none>
```

```bash
k logs my-app-6d788947d8-lpx9k

 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://10.19.62.58:8080
Press CTRL+C to quit
43.247.163.116 - - [24/Aug/2023 17:26:35] "GET / HTTP/1.1" 200 -
207.180.223.28 - - [24/Aug/2023 17:29:25] "CONNECT google.com:443 HTTP/1.1" 404 -
192.99.9.171 - - [24/Aug/2023 17:38:00] "GET /cdn-cgi/trace HTTP/1.1" 404 -
```

```bash
k exec -ti my-app-6d788947d8-lpx9k -- sh

/app # ls
Dockerfile        LICENSE           README.md         requirements.txt  src
```

```bash
k logs nginx

/docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to perform configuration
/docker-entrypoint.sh: Looking for shell scripts in /docker-entrypoint.d/
/docker-entrypoint.sh: Launching /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
```

```bash
k exec -ti nginx -- sh

# ls
bin  boot  dev	docker-entrypoint.d  docker-entrypoint.sh  etc	home  lib  lib32  lib64  libx32  media	mnt  opt  proc	root  run  sbin  srv  sys  tmp	usr  var
```

### What's next?

- Make the CNI plugin host network work with IPAMD plugin, for Ingress to work.
  - Pod IP should be the Labmda Cloud public IP.
- Automate the steps above.
- Research/design the following for the long-term solution:
  - Reliably approve CSRs.
  - Reliably run the SSL passthrough proxy.
  - Set up long-term IAM role for on-prem hosts (see IAM Roles Anywhere).
  - Set up gateway tunnel.
  - EFS should work.
  - See https://github.com/leptonai/lepton/issues/2663 for more.

### NOTES: AWS Client VPN

Basically, using VPC, we can access AWS EKS VPC IPs from VPN-connected Lambda Labs hosts (e.g., connect to EC2 private IPs, EKS control plane endpoints, etc.). But, EKS control plane or EC2 instance cannot route to VPN-connected Lambda Labs hosts.

![vpc-reachability-analysis](./satellite-lambda/vpc-reachability-analysis.png)

This is because all private subnet outbound traffic to `10.0.0.0/16` are routed using the local route table, which has the following route:

![vpc-private-subnet-route-table.png](./satellite-lambda/vpc-private-subnet-route-table.png)

See the following articles for more information:

- [Client-to-client access using AWS Client VPN](https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/scenario-client-to-client.html)
- ["connection can only be initiated from the client to the EC2 instance and it wouldn't work for the connections initiated in the other direction."](https://serverfault.com/questions/964767/unable-to-ping-vpn-clients-from-target-subnet)

Without this step, kubelet exec/logs would not work...

We can still schedule pods on the satellite node, but we cannot access the pod. See below for the remaining steps.

