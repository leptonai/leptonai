# Sattelite EKS node using Ubuntu laptop

**THIS IS EXPERIMENTAL.**

To sum, using a [fargate-kind node object](https://github.com/leptonai/lepton/issues/2267#issuecomment-1673969397) and with some updates to the aws-auth configmap, we can run a satellite node on a Linux laptop to run a simple pod.

## Goals

- On-prem node running outside of VPC can be authorized to join the EKS cluster.
- The node can be stably running sending heartbeats to the EKS cluster.
- The node can run a pod(s).

## Non-goals

- Make coredns work.
- Make sure the node can run Kubernetes deployments with services.

## Prerequisites

- Ubuntu laptop
- EKS cluster
  - We will modity aws-auth configmap so highly recommend against using the existing one.
  - If we modify wrong, you will be locked out of the cluster access.
- `machine` CLI

To install `machine` CLI, run:

```bash
cd ${HOME}/lepton
go build -o /tmp/ma ./machine
/tmp/ma -h
cp /tmp/ma ${GOPATH}/bin/ma

ma a w
```

## Steps

### Download kubeconfig and certs for kubelet

```bash
ma a k k gh055

# or
aws eks update-kubeconfig --region us-east-1 --name gh055
```

```bash
DESCRIBE_CLUSTER_RESULT="/tmp/describe_cluster_result.txt"
aws eks describe-cluster \
--region=us-east-1 \
--name=gh055 \
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

CA_CERTIFICATE_DIRECTORY=/etc/kubernetes/pki
CA_CERTIFICATE_FILE_PATH=$CA_CERTIFICATE_DIRECTORY/ca.crt
sudo mkdir -p $CA_CERTIFICATE_DIRECTORY
sudo chown -R ubuntu $CA_CERTIFICATE_DIRECTORY
echo $B64_CLUSTER_CA | base64 -d > $CA_CERTIFICATE_FILE_PATH
cat $CA_CERTIFICATE_FILE_PATH
cat /etc/kubernetes/pki/ca.crt
```

### Create an ENI

Required for node authorization with `--hostname-override`:

```bash
# to pick subnet ID + security group ID
ma a k l
ma a v g vpc-02f3af6ef3ce509e7

# to create an ENI
ma a n c \
--subnet-id subnet-0a4b3ec9cca34bc10 \
--sg-ids sg-0d3bdbd671a4e34c8 \
--name gh055-fargate-node-test \
--description gh055-fargate-node-test

# to list ENIs
ma a n l

# to get hostname
ma a n g eni-05a32b9e83ef7ae32

# to delete an ENI
# ma a n d eni-05a32b9e83ef7ae32
```

### Update aws-auth configmap to allow the node to join the cluster

Required for node authorization with `--hostname-override`:

```bash
kubectl -n kube-system get configmap aws-auth -o yaml

ma a n g eni-05a32b9e83ef7ae32
```

```yaml
apiVersion: v1
data:
  mapRoles: |
    - groups:
      - system:bootstrappers
      - system:nodes
      rolearn: arn:aws:iam::605454121064:role/gh055-mng-role2
      username: system:node:fargate-ip-10-0-14-131.us-east-1.compute.internal
```

You can get `fargate-ip-10-0-14-131.us-east-1.compute.internal` by running `ma a n g [ENI ID]`.

`arn:aws:iam::605454121064:role/gh055-mng-role2` is a separate role for this node.

If you using an AWS user, update `arn:aws:iam::605454121064:role/gh055-mng-role2` to add your user as a principal, so you can assume the role locally:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
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

(I tried to add `systems:bottstrappers` and `system:nodes` to the user's policy, but it didn't work.)

### Write containerd config

Required for the host network to work:

```toml
# /etc/containerd/config.toml

[grpc]
address = "/run/containerd/containerd.sock"

[plugins."io.containerd.grpc.v1.cri".containerd]
default_runtime_name = "runc"

[plugins."io.containerd.grpc.v1.cri"]
sandbox_image = "602401143452.dkr.ecr.us-east-1.amazonaws.com/eks/pause:3.5"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
runtime_type = "io.containerd.runc.v2"

[plugins."io.containerd.grpc.v1.cri".cni]
bin_dir = "/opt/cni/bin"
conf_dir = "/etc/cni/net.d"
```

```bash
find /etc/cni/net.d/
code /tmp/10-host-network.conf
cat /tmp/10-host-network.conf
sudo cp /tmp/10-host-network.conf /etc/cni/net.d/10-host-network.conf
```

```json
{
	"cniVersion": "0.4.0",
	"name": "host-network",
	"type": "host-local",
	"plugins": [
		{
			"type": "portmap",
			"capabilities": {"portMappings": true}
		}
	],
	"ipam": {
			"type": "host-local",
			"dataDir": "/tmp/cni-host-local",
			"ranges": [
				[{ "subnet": "10.1.2.0/24" }],
				[{ "subnet": "10.1.3.0/24" }]
			]
	}
}
```

```bash
sudo systemctl restart containerd
```

### Write kubelet config

```yaml
# https://kubernetes.io/docs/tasks/administer-cluster/kubelet-config-file/
# https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/
# https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/#kubelet-config-k8s-io-v1beta1-KubeletConfiguration

kind: KubeletConfiguration
apiVersion: kubelet.config.k8s.io/v1beta1

address: 0.0.0.0
port: 10250

authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 2m0s
    enabled: true
  x509:
    clientCAFile: "/etc/kubernetes/pki/ca.crt"
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 5m0s
    cacheUnauthorizedTTL: 30s
clusterDomain: cluster.local
hairpinMode: hairpin-veth
readOnlyPort: 0
cgroupDriver: cgroupfs
cgroupRoot: "/"
featureGates:
  RotateKubeletServerCertificate: true

protectKernelDefaults: true
serializeImagePulls: false
serverTLSBootstrap: true
tlsCipherSuites:
  - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
  - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
  - TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305
  - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
  - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
  - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
  - TLS_RSA_WITH_AES_256_GCM_SHA384
  - TLS_RSA_WITH_AES_128_GCM_SHA256

containerRuntimeEndpoint: unix:///run/containerd/containerd.sock

# running with swap on is not supported, please disable swap! or set --fail-swap-on
failSwapOn: false
registerNode: true
```

### Run fargate node applier command

Only required until the kubelet is successfully registered as a node:

```bash
ma a k n f a \
--region us-east-1 \
--cluster-name gh055 \
--eni-id eni-05a32b9e83ef7ae32 \
--keep=true \
--keep-interval=10s
```

### Run a kubelet

```bash
printf "AWS_ACCESS_KEY_ID=\"%s\" \\
AWS_SECRET_ACCESS_KEY=\"%s\" \\
AWS_SESSION_TOKEN=\"%s\" \\
" \
$(aws sts assume-role \
--role-arn arn:aws:iam::605454121064:role/gh055-mng-role2 \
--role-session-name test \
--query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
--output text)
```

```bash
code /tmp/aaa.sh
sudo bash /tmp/aaa.sh
```

```bash
# /tmp/aaa.sh

AWS_ACCESS_KEY_ID="..." \
AWS_SECRET_ACCESS_KEY="..." \
AWS_SESSION_TOKEN="..." \
/usr/bin/kubelet \
--config /tmp/kubeblet-config.yaml \
--kubeconfig /home/ubuntu/.kube/config \
--container-runtime-endpoint=unix:///run/containerd/containerd.sock \
--image-credential-provider-config /etc/eks/image-credential-provider/config.json \
--image-credential-provider-bin-dir /etc/eks/image-credential-provider \
--hostname-override fargate-ip-10-0-14-131.us-east-1.compute.internal
```

### Make sure node is ready

```bash
NAME                                                STATUS     ROLES    AGE   VERSION
fargate-ip-10-0-14-131.us-east-1.compute.internal   Ready      agent    32s   v1.26.6
```

### Deploy a simple nginx pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  tolerations:
    - key: virtual-kubelet.io/provider
      operator: Equal
      value: ec2
      effect: NoSchedule
  containers:
    - name: nginx-container
      image: nginx:latest
      ports:
        - containerPort: 80
```

```bash
k get po

NAME        READY   STATUS    RESTARTS   AGE
nginx-pod   1/1     Running   0          4m32s
```

Expected error:

> Warning  MissingClusterDNS  8s (x4 over 15s)  kubelet            pod: "nginx-pod_default(ca1526ce-cd18-4a3b-b4a0-70746f96d38f)". kubelet does not have ClusterDNS IP configured and cannot create Pod using "ClusterFirst" policy. Falling back to "Default" policy.
