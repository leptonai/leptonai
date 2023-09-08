
<hr>

# `amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-west-2.20230811.v0.prod`

```bash
aws ssm get-parameters \
--region us-west-2 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

```json
{
    "Parameters": [
        {
            "Name": "/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0e8270ee98210a80e",
            "Version": 19,
            "LastModifiedDate": "2023-08-09T22:29:40.123000+08:00",
            "ARN": "arn:aws:ssm:us-west-2::parameter/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"
        }
    ],
    "InvalidParameters": []
}
```

```bash
cd ${HOME}/lepton/machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-west-2 \
--arch-type amd64-gpu-g4dn-nvidia-t4 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--ssh-ingress-ipv4-cidr 0.0.0.0/0 \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 300 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,ssm-agent,nvidia-driver,nvidia-cuda-toolkit,nvidia-container-toolkit,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# "/etc/eks/containerd/pull-image.sh" only works for ECR images
# and uses "ctr --namespace k8s.io content fetch" which does not help kubelet
# with pull image speedup
#
# https://github.com/leptonai/lepton/blob/main/infra/definitions/warmup_images.json
# https://hub.docker.com/r/nvidia/cuda
# https://us-east-1.console.aws.amazon.com/ecr/repositories/private/605454121064/lepton?region=us-east-1
# https://us-west-2.console.aws.amazon.com/ecr/repositories/private/720771144610/lepton?region=us-west-2
# https://github.com/awslabs/amazon-eks-ami/blob/master/files/pull-image.sh
ecr_password=$(aws ecr get-login-password --region us-west-2)

sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.7 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.8 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.9 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.11 --user AWS:${ecr_password}

# extra ~300 MB per version (not required)
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.7-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.8-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.9-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.11-runner-0.7.2 --user AWS:${ecr_password}

# one-time... once we migrate to new AMIs with common base images, we can skip these
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10-runner-0.1.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10-runner-0.1.12 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/promptai:kosmos2 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:tuna-23.02 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:tuna-23.03 --user AWS:${ecr_password}

sudo ctr --namespace k8s.io images list

# print AMI release information
cat /etc/release-full

df -h
' \
--ec2-key-import \
--image-name-to-create amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-west-2.20230811.v0.prod \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--auto-delete-after-apply-delete-all \
--spec-file-path ./wip/amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-west-2.20230811.v0.prod.yaml
```

```bash
# to download the bootstrap script
scp -i ...ec2-access.key ubuntu@...:/etc/eks/bootstrap.sh ../infra/terraform/eks-lepton/ami-release-artifacts/eks-bootstrap.ubuntu.sh
```

```bash
nvidia-smi

Thu Aug 10 15:21:08 2023
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 530.30.02              Driver Version: 530.30.02    CUDA Version: 12.1     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                  Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf            Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  Tesla T4                        Off| 00000000:00:1E.0 Off |                    0 |
| N/A   42C    P0               28W /  70W|      2MiB / 15360MiB |      4%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+

+---------------------------------------------------------------------------------------+
| Processes:                                                                            |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                             Usage      |
|=======================================================================================|
|  No running processes found                                                           |
+---------------------------------------------------------------------------------------+
```

```bash
/usr/local/cuda-12.1/bin/nvcc --version

nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2023 NVIDIA Corporation
Built on Mon_Apr__3_17:16:06_PDT_2023
Cuda compilation tools, release 12.1, V12.1.105
Build cuda_12.1.r12.1/compiler.32688072_0
```

```bash
BASE_AMI_ID=ami-0e8270ee98210a80e
BUILD_TIME=Thu Aug 10 14:18:18 UTC 2023
BUILD_KERNEL=5.15.0-1040-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.7-0ubuntu1~20.04.1"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.7.2 "
CTR_VERSION="ctr github.com/containerd/containerd 1.7.2"

KUBELET_VERSION=""
```

Image ID:

```text
ami-072faa66fd0b86a90
```

<hr>

# `amd64-cpu.eks-1.26.ubuntu20.04.us-west-2.20230811.v0.prod`

```bash
aws ssm get-parameters \
--region us-west-2 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

```json
{
    "Parameters": [
        {
            "Name": "/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0e8270ee98210a80e",
            "Version": 19,
            "LastModifiedDate": "2023-08-09T22:29:40.123000+08:00",
            "ARN": "arn:aws:ssm:us-west-2::parameter/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"
        }
    ],
    "InvalidParameters": []
}
```

```bash
cd ${HOME}/lepton/machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-west-2 \
--arch-type amd64 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--ssh-ingress-ipv4-cidr 0.0.0.0/0 \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 300 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,ssm-agent,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# "/etc/eks/containerd/pull-image.sh" only works for ECR images
# and uses "ctr --namespace k8s.io content fetch" which does not help kubelet
# with pull image speedup
#
# https://github.com/leptonai/lepton/blob/main/infra/definitions/warmup_images.json
# https://hub.docker.com/r/nvidia/cuda
# https://us-east-1.console.aws.amazon.com/ecr/repositories/private/605454121064/lepton?region=us-east-1
# https://us-west-2.console.aws.amazon.com/ecr/repositories/private/720771144610/lepton?region=us-west-2
# https://github.com/awslabs/amazon-eks-ami/blob/master/files/pull-image.sh
ecr_password=$(aws ecr get-login-password --region us-west-2)

sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.7 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.8 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.9 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.11 --user AWS:${ecr_password}

# extra ~300 MB per version (not required)
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.7-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.8-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.9-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.11-runner-0.7.2 --user AWS:${ecr_password}

# one-time... once we migrate to new AMIs with common base images, we can skip these
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10-runner-0.1.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:photon-py3.10-runner-0.1.12 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/promptai:kosmos2 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:tuna-23.02 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 720771144610.dkr.ecr.us-west-2.amazonaws.com/lepton:tuna-23.03 --user AWS:${ecr_password}

# print AMI release information
cat /etc/release-full

df -h
' \
--ec2-key-import \
--image-name-to-create amd64-cpu.eks-1.26.ubuntu20.04.us-west-2.20230811.v0.prod \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--spec-file-path ./wip/amd64-cpu.eks-1.26.ubuntu20.04.us-west-2.20230811.v0.prod.yaml
```

```bash
# to download the bootstrap script
scp -i ...ec2-access.key ubuntu@...:/etc/eks/bootstrap.sh ../infra/terraform/eks-lepton/ami-release-artifacts/eks-bootstrap.ubuntu.sh
```

```bash
BASE_AMI_ID=ami-0e8270ee98210a80e
BUILD_TIME=Thu Aug 10 14:13:27 UTC 2023
BUILD_KERNEL=5.15.0-1040-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.7-0ubuntu1~20.04.1"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.7.2 "
CTR_VERSION="ctr github.com/containerd/containerd 1.7.2"

KUBELET_VERSION=""
```

Image ID:

```text
ami-086eaf7fcdadfa0f8
```

<hr>

# `amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-east-1.20230811.v0.dev`

```bash
aws ssm get-parameters \
--region us-east-1 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

```json
{
    "Parameters": [
        {
            "Name": "/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0f72b79de992a6ff6",
            "Version": 19,
            "LastModifiedDate": "2023-08-09T22:29:23.047000+08:00",
            "ARN": "arn:aws:ssm:us-east-1::parameter/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"
        }
    ],
    "InvalidParameters": []
}
```

```bash
cd ${HOME}/lepton/machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64-gpu-g4dn-nvidia-t4 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--ssh-ingress-ipv4-cidr 0.0.0.0/0 \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 300 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,ssm-agent,nvidia-driver,nvidia-cuda-toolkit,nvidia-container-toolkit,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# "/etc/eks/containerd/pull-image.sh" only works for ECR images
# and uses "ctr --namespace k8s.io content fetch" which does not help kubelet
# with pull image speedup
#
# https://github.com/leptonai/lepton/blob/main/infra/definitions/warmup_images.json
# https://hub.docker.com/r/nvidia/cuda
# https://us-east-1.console.aws.amazon.com/ecr/repositories/private/605454121064/lepton?region=us-east-1
# https://us-west-2.console.aws.amazon.com/ecr/repositories/private/720771144610/lepton?region=us-west-2
# https://github.com/awslabs/amazon-eks-ami/blob/master/files/pull-image.sh
ecr_password=$(aws ecr get-login-password --region us-east-1)

sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.8 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.9 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.11 --user AWS:${ecr_password}

# extra ~300 MB per version (not required)
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.8-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.9-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.11-runner-0.7.2 --user AWS:${ecr_password}

# one-time... once we migrate to new AMIs with common base images, we can skip these
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.1.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.1.12 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/promptai:kosmos2 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-23.02 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-23.03 --user AWS:${ecr_password}

# print AMI release information
cat /etc/release-full

df -h
' \
--ec2-key-import \
--image-name-to-create amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-east-1.20230811.v0.dev \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--spec-file-path ./wip/amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-east-1.20230811.v0.dev.yaml
```

```bash
# to download the bootstrap script
scp -i ...ec2-access.key ubuntu@...:/etc/eks/bootstrap.sh ../infra/terraform/eks-lepton/ami-release-artifacts/eks-bootstrap.ubuntu.sh
```

```bash
BASE_AMI_ID=ami-0f72b79de992a6ff6
BUILD_TIME=Thu Aug 10 14:42:30 UTC 2023
BUILD_KERNEL=5.15.0-1040-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.7-0ubuntu1~20.04.1"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.7.2 "
CTR_VERSION="ctr github.com/containerd/containerd 1.7.2"

KUBELET_VERSION=""
```

```text
Thu Aug 10 15:37:11 2023
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 530.30.02              Driver Version: 530.30.02    CUDA Version: 12.1     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                  Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf            Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  Tesla T4                        Off| 00000000:00:1E.0 Off |                    0 |
| N/A   40C    P0               26W /  70W|      2MiB / 15360MiB |      4%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+

+---------------------------------------------------------------------------------------+
| Processes:                                                                            |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                             Usage      |
|=======================================================================================|
|  No running processes found                                                           |
+---------------------------------------------------------------------------------------+
```

```bash
/usr/local/cuda-12.1/bin/nvcc --version

nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2023 NVIDIA Corporation
Built on Mon_Apr__3_17:16:06_PDT_2023
Cuda compilation tools, release 12.1, V12.1.105
Build cuda_12.1.r12.1/compiler.32688072_0
```

Image ID:

```text
ami-06a3d0a4109189f64
```

<hr>

# `amd64-cpu.eks-1.26.ubuntu20.04.us-east-1.20230811.v0.dev`

```bash
aws ssm get-parameters \
--region us-east-1 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

```json
{
    "Parameters": [
        {
            "Name": "/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0f72b79de992a6ff6",
            "Version": 19,
            "LastModifiedDate": "2023-08-09T22:29:23.047000+08:00",
            "ARN": "arn:aws:ssm:us-east-1::parameter/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"
        }
    ],
    "InvalidParameters": []
}
```

```bash
cd ${HOME}/lepton/machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--ssh-ingress-ipv4-cidr 0.0.0.0/0 \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 300 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,ssm-agent,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# "/etc/eks/containerd/pull-image.sh" only works for ECR images
# and uses "ctr --namespace k8s.io content fetch" which does not help kubelet
# with pull image speedup
#
# https://github.com/leptonai/lepton/blob/main/infra/definitions/warmup_images.json
# https://hub.docker.com/r/nvidia/cuda
# https://us-east-1.console.aws.amazon.com/ecr/repositories/private/605454121064/lepton?region=us-east-1
# https://us-west-2.console.aws.amazon.com/ecr/repositories/private/720771144610/lepton?region=us-west-2
# https://github.com/awslabs/amazon-eks-ami/blob/master/files/pull-image.sh
ecr_password=$(aws ecr get-login-password --region us-east-1)

sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.8 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.9 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.11 --user AWS:${ecr_password}

# extra ~300 MB per version (not required)
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.8-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.9-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.7.2 --user AWS:${ecr_password}
# sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.11-runner-0.7.2 --user AWS:${ecr_password}

# one-time... once we migrate to new AMIs with common base images, we can skip these
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.1.10 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.1.12 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/promptai:kosmos2 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-23.02 --user AWS:${ecr_password}
sudo ctr --namespace k8s.io images pull 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:tuna-23.03 --user AWS:${ecr_password}

# print AMI release information
cat /etc/release-full

df -h
' \
--ec2-key-import \
--image-name-to-create amd64-cpu.eks-1.26.ubuntu20.04.us-east-1.20230811.v0.dev \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--spec-file-path ./wip/amd64-cpu.eks-1.26.ubuntu20.04.us-east-1.20230811.v0.dev.yaml
```

```bash
# to download the bootstrap script
scp -i ...ec2-access.key ubuntu@...:/etc/eks/bootstrap.sh ../infra/terraform/eks-lepton/ami-release-artifacts/eks-bootstrap.ubuntu.sh
```

```bash
BASE_AMI_ID=ami-0f72b79de992a6ff6
BUILD_TIME=Thu Aug 10 14:40:54 UTC 2023
BUILD_KERNEL=5.15.0-1040-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.7-0ubuntu1~20.04.1"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.7.2 "
CTR_VERSION="ctr github.com/containerd/containerd 1.7.2"

KUBELET_VERSION=""
```

Image ID:

```text
ami-02b84469855034b61
```

<hr>

# `amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-west-2.20230720.v0`

```bash
aws ssm get-parameters \
--region us-west-2 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

```json
{
    "Parameters": [
        {
            "Name": "/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0e425174814918692",
            "Version": 14,
            "LastModifiedDate": "2023-07-15T06:49:44.262000-07:00",
            "ARN": "arn:aws:ssm:us-west-2::parameter/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"
        }
    ],
    "InvalidParameters": []
}
```

```bash
cd ./machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-west-2 \
--arch-type amd64-gpu-g4dn-nvidia-t4 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 100 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,nvidia-driver,nvidia-cuda-toolkit,nvidia-container-toolkit,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# to use containerd
sudo systemctl stop docker || true
sudo systemctl disable docker || true
df -h

# print AMI release information
cat /etc/release-full
' \
--ec2-key-import \
--image-name-to-create amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-west-2.20230720.v0 \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--auto-delete-after-apply-delete-all \
--spec-file-path ./wip/amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-west-2.20230720.v0.yaml
```

```bash
BASE_AMI_ID=ami-0e425174814918692
BUILD_TIME=Fri Jul 21 05:12:24 UTC 2023
BUILD_KERNEL=5.15.0-1039-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.4-0ubuntu1~20.04.3"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3 "
CTR_VERSION="ctr github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3"

KUBELET_VERSION=""
```

Image ID:

```text
ami-0525c008f4e0dee62
```

<hr>

# `amd64-cpu.eks-1.26.ubuntu20.04.us-west-2.20230720.v0`

```bash
aws ssm get-parameters \
--region us-west-2 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

```json
{
    "Parameters": [
        {
            "Name": "/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0e425174814918692",
            "Version": 14,
            "LastModifiedDate": "2023-07-15T06:49:44.262000-07:00",
            "ARN": "arn:aws:ssm:us-west-2::parameter/aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"
        }
    ],
    "InvalidParameters": []
}
```

```bash
cd ./machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-west-2 \
--arch-type amd64 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 100 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# to use containerd
sudo systemctl stop docker || true
sudo systemctl disable docker || true
df -h

# print AMI release information
cat /etc/release-full
' \
--ec2-key-import \
--image-name-to-create amd64-cpu.eks-1.26.ubuntu20.04.us-west-2.20230720.v0 \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--auto-delete-after-apply-delete-all \
--spec-file-path ./wip/amd64-cpu.eks-1.26.ubuntu20.04.us-west-2.20230720.v0.yaml
```

```bash
BASE_AMI_ID=ami-0e425174814918692
BUILD_TIME=Fri Jul 21 04:57:22 UTC 2023
BUILD_KERNEL=5.15.0-1039-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.4-0ubuntu1~20.04.3"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3 "
CTR_VERSION="ctr github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3"

KUBELET_VERSION=""
```

Image ID:

```text
ami-0dfcb28cf6bf4142f
```

<hr>

# `amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-east-1.20230719.v0`

```bash
cd ./machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64-gpu-g4dn-nvidia-t4 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 100 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,nvidia-driver,nvidia-cuda-toolkit,nvidia-container-toolkit,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# to use containerd
sudo systemctl stop docker || true
sudo systemctl disable docker || true
df -h

# print AMI release information
cat /etc/release-full
' \
--ec2-key-import \
--image-name-to-create amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-east-1.20230719.v0 \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--auto-delete-after-apply-delete-all \
--spec-file-path ./wip/amd64-gpu.g4dn-nvidia-t4.eks-1.26.ubuntu20.04.us-east-1.20230719.v0.yaml
```

```bash
BASE_AMI_ID=ami-04d64ac76bcedca9c
BUILD_TIME=Wed Jul 19 08:30:13 UTC 2023
BUILD_KERNEL=5.15.0-1039-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.4-0ubuntu1~20.04.3"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3 "
CTR_VERSION="ctr github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3"

KUBELET_VERSION=""
```

Image ID:

```text
ami-0f5cfba4a72f3af0d
```

<hr>

# `amd64-cpu.eks-1.26.ubuntu20.04.us-east-1.20230719.v0`

```bash
cd ./machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 100 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# to use containerd
sudo systemctl stop docker || true
sudo systemctl disable docker || true
df -h

# print AMI release information
cat /etc/release-full
' \
--ec2-key-import \
--image-name-to-create amd64-cpu.eks-1.26.ubuntu20.04.us-east-1.20230719.v0 \
--wait-for-init-script-completion \
--wait-for-image-create-completion \
--auto-delete-after-apply \
--auto-delete-after-apply-delete-all \
--spec-file-path ./wip/amd64-cpu.eks-1.26.ubuntu20.04.us-east-1.20230719.v0.yaml
```

```bash
BASE_AMI_ID=ami-04d64ac76bcedca9c
BUILD_TIME=Wed Jul 19 08:11:27 UTC 2023
BUILD_KERNEL=5.15.0-1039-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.4-0ubuntu1~20.04.3"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3 "
CTR_VERSION="ctr github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3"

KUBELET_VERSION=""
```

Image ID:

```text
ami-0fb2155d0930fa381
```

<hr>

# `amd64-gpu-g4dn-nvidia-t4.eks.ubuntu20.04.us-east-1.20230705.v0`

```bash
machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64-gpu-g4dn-nvidia-t4 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 100 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,nvidia-driver,nvidia-cuda-toolkit,nvidia-container-toolkit,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# to use containerd
sudo systemctl stop docker || true
sudo systemctl disable docker || true

# https://us-east-1.console.aws.amazon.com/ecr/repositories/private/605454121064/lepton?region=us-east-1
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.8-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.9-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.11-runner-0.1.7

# print AMI release information
cat /etc/release-full

df -h

INSTANCE_ID=$(imds /latest/meta-data/instance-id)
echo ${INSTANCE_ID}
' \
--ec2-key-import \
--wait-for-init-script-completion \
--image-name-to-create amd64-gpu-g4dn-nvidia-t4.eks.ubuntu20.04.us-east-1.20230705.v0 \
--wait-for-image-create-completion \
--spec-file-path wip/amd64-gpu-g4dn-nvidia-t4.ubuntu20.04-ami-reuse.yaml
```

Final AMI release information:

```text
ami-0b10f260913ad7e15
```

Detailed release information:

```bash
$ cat /etc/release-full

BASE_AMI_ID=ami-08ec00f2cedeae247
BUILD_TIME=Wed Jul  5 23:54:33 UTC 2023
BUILD_KERNEL=5.15.0-1039-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.4-0ubuntu1~20.04.3"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3 "
CTR_VERSION="ctr github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3"

KUBELET_VERSION=""
```

<hr>

# `amd64-cpu.eks.ubuntu20.04.us-east-1.20230705.v0`

```bash
machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64 \
--os-type ubuntu20.04 \
--id-prefix eks-ami \
--image-id-ssm-parameter /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id \
--image-volume-type gp3 \
--image-volume-size-in-gb 100 \
--image-volume-iops 3000 \
--plugins imds,provider-id,vercmp,time-sync,eks-worker-node-ami-reuse,ami-info,cleanup-image-packages,cleanup-image-ssh-keys \
--post-init-script '
# to use containerd
sudo systemctl stop docker || true
sudo systemctl disable docker || true

# https://us-east-1.console.aws.amazon.com/ecr/repositories/private/605454121064/lepton?region=us-east-1
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.7-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.8-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.9-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.10-runner-0.1.7
/etc/eks/containerd/pull-image.sh 605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py3.11-runner-0.1.7

# print AMI release information
cat /etc/release-full

df -h

INSTANCE_ID=$(imds /latest/meta-data/instance-id)
echo ${INSTANCE_ID}
' \
--ec2-key-import \
--wait-for-init-script-completion \
--image-name-to-create amd64-cpu.eks.ubuntu20.04.us-east-1.20230705.v0 \
--wait-for-image-create-completion \
--spec-file-path wip/amd64-cpu.ubuntu20.04-ami-reuse.yaml
```

Final AMI release information:

```text
ami-04b8af3864f78166e
```

Detailed release information:

```bash
$ cat /etc/release-full

BASE_AMI_ID=ami-08ec00f2cedeae247
BUILD_TIME=Wed Jul  5 23:42:51 UTC 2023
BUILD_KERNEL=5.15.0-1039-aws
ARCH=x86_64

OS_RELEASE_ID=ubuntu
OS_RELEASE_DISTRIBUTION=ubuntu20.04

RUNC_VERSION="runc version 1.1.4-0ubuntu1~20.04.3"
CONTAINERD_VERSION="containerd github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3 "
CTR_VERSION="ctr github.com/containerd/containerd 1.6.12-0ubuntu1~20.04.3"

KUBELET_VERSION=""
```
