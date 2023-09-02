# Sattelite EKS node using Lambda Labs

**THIS IS EXPERIMENTAL AND INTENTIONALLY NOT AUTOMATED.**

To sum, any Lambda machine can be an EKS node outside of AWS as long as it's created as a [fargate-kind node](https://github.com/leptonai/lepton/issues/2267#issuecomment-1673969397), and with host networking, we can run pods on the satellite node. And with extra steps, `kubectl logs` and `exec` works.

## Goals

- On-prem node outside of AWS can be authorized to join the EKS cluster.
- The node stably runs sending heartbeats to the EKS cluster.
- The node runs a pod(s).
- The node runs Kubernetes deployments with services, using Node IP.
- kubelet logs and exec work.
- Run GPU-enabled photon workloads.

See the following issues for more:

- [GH#2267](https://github.com/leptonai/lepton/issues/2267)
- [GH#2663](https://github.com/leptonai/lepton/issues/2663)

## Non-goals

Connecting via VPN does not work due to limitations in AWS Client VPN -- see [NOTES: AWS Client VPN](#notes-aws-client-vpn).

Thus, requires us to set up SSL passthrough proxy.

Full automation is not a goal for now.

## Step 1. Set up tools

`machine` CLI (helper tool to create ENI resources):

```bash
cd ${HOME}/lepton
go build -o /tmp/ma ./machine
/tmp/ma -h
cp /tmp/ma ${GOPATH}/bin/ma

ma aws whoami
```

## Step 2. Create/pick a cluster to create a node

- We will modify aws-auth configmap -- highly recommend against using the existing one if it's for experimentation.
- Wrong aws-auth configmap can lock you out of the cluster access.

## Step 3. Create a Lambda Cloud instance for the satellite node

```bash
# to save Lambda Cloud token in your local machine
# go to Lamba Cloud to get the token
ma lambda-labs save-token secret_...
```

```bash
# to prepare the SSH key
ma lambda-labs ssh-keys ls
ma lambda-labs ssh-keys create gyuho-test
```

```bash
# to list instances
ma lambda-labs instances types
ma lambda-labs instances ls

# to create an instance
ma lambda-labs instances create \
--name gyuho-test \
--instance-type gpu_1x_a10 \
--region us-west-1 \
--ssh-key-names gyuho-test
```

## Step 4. Install dependencies in Lambda Cloud instance

We need to install kubelet, containerd, and CNI components.

Note that Lambda Cloud instance has alreadys installed `aws`, `docker`, `containerd`, `runc` installed.

Unless needed, just use the one the Lambda Cloud machine already has.

```bash
# "192.9.227.8" is the Lambda Cloud machine public IP
ssh -o "StrictHostKeyChecking no" -i ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8

# aws, docker, containerd, runc are already installed
# just install CNI plugins and others
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/init.bash ubuntu@192.9.227.8:/tmp/init.bash
```

```bash
# to trigger the installation
ssh -o "StrictHostKeyChecking no" -i ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 '

tail -100 /tmp/init.bash
rm -f /tmp/init.bash.log
sudo bash /tmp/init.bash >> /tmp/init.bash.log 2>&1 &
tail -200 /tmp/init.bash.log

'
```

```bash
# to check the status of init script
ssh -o "StrictHostKeyChecking no" -i ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 '

tail -200 /tmp/init.bash.log
find /etc/cni/net.d

'
```

Optionally, prefetch the container images:

```bash
ecr_password=$(
AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
aws ecr get-login-password --region us-east-1)

sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7 --user AWS:${ecr_password}
# ....
```

## Step 5. Create EC2 instance to proxy apiserver traffic

To pick the subnet ID and security group ID of an existing EKS cluster:

```bash
# to pick subnet ID + security group ID
ma aws --region us-east-1 eks ls
ma aws --region us-east-1 vpc get vpc-09526631a1787f5a3
```

```bash
cd $HOME/lepton/machine-rs
./scripts/build.release.sh
```

```bash
# for sg, pick "EKS created security group applied" or "Secondary EKS cluster security group to allow traffic from/to nodes"
# for subnet, pick "private-us-east-1a"
cd $HOME/lepton/machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64 \
--os-type ubuntu22.04 \
--image-volume-type gp3 \
--image-volume-size-in-gb 40 \
--image-volume-iops 3000 \
--existing-vpc-subnet-ids-for-asg subnet-01c298209807aa517 \
--existing-vpc-security-group-ids sg-0056db63dc3111b5c \
--id-prefix sat-proxy \
--plugins imds,provider-id,time-sync,system-limit-bump,aws-cli,ssm-agent,cloudwatch-agent,cleanup-image-packages \
--spec-file-path ./satellite-proxy-dev-machine/amd64-cpu.ubuntu22.04.us-east-1.yaml
```

```bash
# run the following to delete all resources including the S3 bucket WITHOUT PROMPT
./target/release/machine-rs aws delete \
--delete-all \
--skip-prompt \
--spec-file-path ./satellite-proxy-dev-machine/amd64-cpu.ubuntu22.04.us-east-1.yaml
```

## Step 6. Set up and start satellite-proxy.service

Now we need to set up a systemd service to start the proxy server.

First, we need to compile or download the binary to the remote machine:

```bash
cd $HOME/lepton/satellite/proxy
GOOS=linux GOARCH=amd64 go build -v .
```

Or download from our dev account:

```bash
aws s3 ls s3://lepton-internal-binaries
aws s3 cp s3://lepton-internal-binaries/satellite-proxy-amd64-linux /tmp/satellite-proxy-amd64-linux
```

Now using SSM to run remote commands (or SSH/SSM into the machine):

```bash
EC2_INSTANCE_ID=${EC2_INSTANCE_ID}
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID}
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo tail -10 /var/log/cloud-init-output.log"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartInteractiveCommand' --parameters command="bash -l"

# "sat-proxy-202309-2thdq7z-us-east-1/sat-proxy-202309-2epxtJ" is the bucket/s3 directory name
# that this machine has access to
aws s3 cp /tmp/satellite-proxy-amd64-linux s3://sat-proxy-202309-2thdq7z-us-east-1/sat-proxy-202309-2epxtJ/bin/satellite-proxy-amd64-linux
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="aws s3 cp s3://sat-proxy-202309-2thdq7z-us-east-1/sat-proxy-202309-2epxtJ/bin/satellite-proxy-amd64-linux /tmp/satellite-proxy-amd64-linux"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="chmod +x /tmp/satellite-proxy-amd64-linux"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo cp /tmp/satellite-proxy-amd64-linux /usr/bin/satellite-proxy"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="satellite-proxy -h"

aws ec2 describe-instances \
--region us-east-1 \
--instance-ids ${EC2_INSTANCE_ID} \
--query "Reservations[0].Instances[0].PrivateIpAddress" \
--output text
# 10.0.9.83

aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo rm -f /var/log/satellite-proxy.log"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="rm -f /tmp/satellite-proxy.service"
cat << 'EOF' > /tmp/satellite-proxy.service
[Unit]
Description=satellite-proxy

[Service]
Type=simple
TimeoutStartSec=300
Restart=always
User=root
Group=root
RestartSec=5s
LimitNOFILE=40000
ExecStart=/usr/bin/satellite-proxy "10.0.9.83" "192.9.227.8" "10250,443,80,8080"
StandardOutput=append:/var/log/satellite-proxy.log
StandardError=append:/var/log/satellite-proxy.log

[Install]
WantedBy=multi-user.target
EOF
aws s3 cp /tmp/satellite-proxy.service s3://sat-proxy-202309-2thdq7z-us-east-1/sat-proxy-202309-2epxtJ/satellite-proxy.service
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="aws s3 cp s3://sat-proxy-202309-2thdq7z-us-east-1/sat-proxy-202309-2epxtJ/satellite-proxy.service /tmp/satellite-proxy.service"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo cp /tmp/satellite-proxy.service /etc/systemd/system/satellite-proxy.service"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo systemctl daemon-reload"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo cat /etc/systemd/system/satellite-proxy.service"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo systemctl restart --no-block satellite-proxy.service"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo systemctl status satellite-proxy.service"
aws ssm start-session --region us-east-1 --target ${EC2_INSTANCE_ID} --document-name 'AWS-StartNonInteractiveCommand' --parameters command="sudo tail /var/log/satellite-proxy.log"
```

## Step 7. Create an ENI for the satellite node

- Most tricky part, and EKS- and satellite-node-specific
- NOT officially documented and discovered by some reverse engineering (see [source](https://github.com/leptonai/lepton/issues/2267#issuecomment-1673969397))
- Only required for the satellite node authorization

```bash
# to pick subnet ID + security group ID
ma aws --region us-east-1 eks ls
ma aws --region us-east-1 vpc get vpc-09526631a1787f5a3

# to create an ENI
# pick private subnet
# pick "Secondary EKS cluster security group to allow traffic from/to nodes" sg
ma aws --region us-east-1 enis create \
--subnet-id subnet-01c298209807aa517 \
--sg-ids sg-0056db63dc3111b5c \
--name gh70-satellite-node-01 \
--description gh70-satellite-node-01

# to list ENIs
ma aws --region us-east-1 enis ls
ma aws --region us-east-1 enis get eni-01626feee6391533e
```

```text
*-----------------------*------------------------*------------*------------*----------------------------*-----------------------*--------------------------*------------*----------------------*
|        ENI ID         |    ENI DESCRIPTION     | ENI STATUS | PRIVATE IP |        PRIVATE DNS         |        VPC ID         |        SUBNET ID         |     AZ     |         SGS          |
*-----------------------*------------------------*------------*------------*----------------------------*-----------------------*--------------------------*------------*----------------------*
| eni-01626feee6391533e | gh70-satellite-node-01 | available  | 10.0.9.178 | ip-10-0-9-178.ec2.internal | vpc-09526631a1787f5a3 | subnet-01c298209807aa517 | us-east-1a | sg-0056db63dc3111b5c |
*-----------------------*------------------------*------------*------------*----------------------------*-----------------------*--------------------------*------------*----------------------*
```

And this fargate hostname is required for later node registration:

```bash
ma aws --region us-east-1 eks nodes satellite hostname eni-01626feee6391533e
# fargate-ip-10-0-9-178.us-east-1.compute.internal
```

Why `fargate-`? We don't know why. We just know this is required by EKS.

```bash
# to delete an ENI
# ma aws --region us-east-1 enis delete eni-01626feee6391533e
```

## Step 8. Add the role ARN for the satellite node

```bash
ma aws --region us-east-1 eks nodes satellite hostname eni-01626feee6391533e
# fargate-ip-10-0-9-178.us-east-1.compute.internal

ma aws --region us-east-1 eks aws-auth get gh70
ma aws --region us-east-1 eks aws-auth add \
--cluster-name gh70 \
--groups system:bootstrappers,system:nodes \
--user-name system:node:fargate-ip-10-0-9-178.us-east-1.compute.internal \
--role-arn arn:aws:iam::605454121064:role/gh70-satellite

kubectl -n kube-system edit configmap aws-auth
kubectl -n kube-system get configmap aws-auth -o yaml

```

## Step 9. Transfer artifacts/dependencies into the satellite node

```bash
# "kubelet --node-ip=[empty]" defaults to the "internal" IP address of the Lambda Cloud instance
# "kubelet --node-ip=[Lambda public IP]" does not work because "not found in the host's network interfaces"
# "kubelet --node-ip=[EC2 proxy machine private IP]" only works iff proxy server is running to forward all apiserver traffic
# "kubelet --node-ip=[EC2 ENI private IP]" does not work
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

ExecStart=/usr/bin/kubelet.bash \
[aws access key of satellite-node user] \
[aws secret key of satellite-node user] \
us-east-1 \
gh70 \
arn:aws:iam::605454121064:role/gh70-satellite \
fargate-ip-10-0-9-178.us-east-1.compute.internal \
"lepton.ai/resource-provider=lambdalabs,eks.amazonaws.com/compute-type=fargate,nvidia.com/gpu.product=NVIDIA-A10G,k8s.amazonaws.com/accelerator=NVIDIA-A10G" \
10.0.9.83

StandardOutput=append:/var/log/kubelet.log
StandardError=append:/var/log/kubelet.log

[Install]
WantedBy=multi-user.target
EOF

scp -i ~/.lambda-labs/ssh.private.pem /tmp/kubelet.service ubuntu@192.9.227.8:/tmp/kubelet.service
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/kubelet.yaml ubuntu@192.9.227.8:/tmp/kubelet.yaml
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/kubelet.bash ubuntu@192.9.227.8:/tmp/kubelet.bash
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/kubelet.timer ubuntu@192.9.227.8:/tmp/kubelet.timer
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/containerd.toml ubuntu@192.9.227.8:/tmp/containerd.toml
scp -i ~/.lambda-labs/ssh.private.pem ./satellite-lambda/cni.json ubuntu@192.9.227.8:/tmp/cni.json

ssh -o "StrictHostKeyChecking no" -i ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 '
sudo cp /tmp/kubelet.yaml /etc/kubernetes/kubelet/kubelet.yaml
sudo chmod +x /tmp/kubelet.bash && sudo cp /tmp/kubelet.bash /usr/bin/kubelet.bash
sudo cp /tmp/kubelet.service /etc/systemd/system/kubelet.service
sudo cp /tmp/kubelet.timer /etc/systemd/system/kubelet.timer
sudo cp /tmp/containerd.toml /etc/containerd/config.toml
sudo rm -f /etc/cni/net.d/* && sudo cp /tmp/cni.json /etc/cni/net.d/10-host-network.conflist
# sudo chmod +x /tmp/cni-debug-amd64-linux && sudo cp /tmp/cni-debug-amd64-linux /opt/cni/bin/debug
'
```

## Step 10. Start and restart kubelet service

This can be done in many ways, and will be automated in the future.

For simplicity, we just use `scp` to copy the files:

```bash
ssh -o "StrictHostKeyChecking no" ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 '
sudo systemctl daemon-reload
sudo systemctl stop kubelet.service
sudo systemctl disable kubelet.service
sudo systemctl disable kubelet.timer

sudo rm -f /var/log/kubelet.log

sudo systemctl enable kubelet.service
sudo systemctl restart --no-block kubelet.service
sudo systemctl enable kubelet.timer
sudo systemctl start kubelet.timer
sudo systemctl list-timers
'

sleep 5

# to check status
ssh -o "StrictHostKeyChecking no" ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 'sudo systemctl status containerd'
ssh -o "StrictHostKeyChecking no" ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 'sudo systemctl status kubelet.service'
ssh -o "StrictHostKeyChecking no" ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 'sudo tail -200 /var/log/kubelet.log'

# to stop
ssh -o "StrictHostKeyChecking no" ~/.lambda-labs/ssh.private.pem ubuntu@192.9.227.8 '
sudo systemctl list-timers
sudo systemctl daemon-reload
sudo systemctl stop kubelet.service
sudo systemctl disable kubelet.service
sudo systemctl disable kubelet.timer
'
```

## Step 11. Install NVIDIA k8s device plugin

```bash
# required to have status.allocatable."nvidia.com/gpu: 1"
# required to have status.capacity."nvidia.com/gpu: 1"
k apply -f ./satellite-lambda/nvidia-k8s-device-plugin.yaml
k -n kube-system get po -o wide
k get nodes
k get nodes fargate-ip-10-0-9-178.us-east-1.compute.internal -o yaml
```

## Step 12. Test ingress

```bash
k apply -f ./satellite-lambda/2048.yaml
k -n game-2048 get po -o wide
k -n game-2048 get ingress
k delete -f ./satellite-lambda/2048.yaml
```

And connect to the service using the Lambda Labs instance public IP + port 8080:

![2048-demo](satellite-lambda/2048-demo.png)

### NOTES: Debug CSR

Inspect the certificate with:

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
    - arn:aws:sts::605454121064:assumed-role/gh70-satellite/test
    canonicalArn:
    - arn:aws:iam::605454121064:role/gh70-satellite
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
  username: system:node:fargate-ip-10-0-9-178.us-east-1.compute.internal
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
        Subject: O = system:nodes, CN = system:node:fargate-ip-10-0-9-178.us-east-1.compute.internal
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
                DNS:fargate-ip-10-0-9-178.us-east-1.compute.internal, IP Address:10.0.2.233
    Signature Algorithm: sha256WithRSAEncryption
```

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

