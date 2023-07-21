# `machine-rs`

Single command to spin up a development machine on cloud, with focus on clean-ups.

## Features and roadmap

Currently only support AWS, as they have excellent Rust SDK supports (AWS).

- Automates machine image builds for custom nodes (e.g., Ubuntu AMIs with GPU driver installation).
- Spin up a dev machine in AWS/Lambda cloud/*.
- Automates SSH key management.
- Installs virtual kubelet dependencies on remote machines.
- Pauses the dev machine, when you are not using it.
- Statically provisions an EBS volume, so even with the pause, your data remain intact.
- Statically provisions an Elastic IP (EIP).
- Configures and installs all dependencies (e.g., Python, NVIDIA/CUDA drivers).

## Example

```bash
cd ./machine-rs
./scripts/build.release.sh

cd ./machine-rs
./target/release/machine-rs aws default-spec -h

cd ./machine-rs
./target/release/machine-rs aws default-spec \
--instance-mode on-demand \
--instance-size 2xlarge \
--ip-mode ephemeral \
--region us-east-1 \
--arch-type amd64 \
--os-type ubuntu22.04 \
--id-prefix my-dev \
--plugins imds,provider-id,vercmp,setup-local-disks,mount-bpf-fs,time-sync,system-limit-bump,aws-cli,ssm-agent,cloudwatch-agent,static-volume-provisioner,anaconda,go,docker,aws-cfn-helper,ecr-credential-helper,ecr-credential-provider,kubectl,helm,terraform,ami-info,cleanup-image-packages \
--post-init-script '

df -h

INSTANCE_ID=$(imds /latest/meta-data/instance-id)
echo ${INSTANCE_ID}

' \
--wait-for-init-script-completion \
--spec-file-path ./wip/amd64-cpu.ubuntu22.04-dev-machine.yaml
```
