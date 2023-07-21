
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
