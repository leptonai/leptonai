
# Node group AMIs

To summarize, the custom Ubuntu AMI + NVIDIA driver + pre-fetched Lepton container images is the best option, the platform that NVIDIA supports the most (see [NVIDIA/gpu-operator/issues/227](https://github.com/NVIDIA/gpu-operator/issues/227)). But, this can be cutting edge, unstable sometimes (see [launchpad/cloud-images/2012689](https://bugs.launchpad.net/cloud-images/+bug/2012689)). Alternatively, we can use the default Amazon Linux 2 (AL2) AMI, but the NVIDIA GPU operator does not work on AL2, which also breaks the `cluster-autoscaler` scale-downs.

We should use Ubuntu wherever we need the GPU operator but have a way to fall back to AL2 if something goes wrong with the Ubuntu AMI.

## AL2 and AL2_GPU AMI

The official AMI type from EKS for CPU/GPU platforms.

The AMI build script can be found at [`awslabs/amazon-eks-ami`](https://github.com/awslabs/amazon-eks-ami).

**Pros**:

- Works for any workloads.
- Official support from AWS EKS.
- No need for manual AMI updates (e.g., Linux kernel security patches), handled by EKS node group team.

**Cons**:

- The default image does not cache Lepton-specific container images at the AMI layer.
  - We can pre-fetch during node bootstrap, but this can slow down the new node launch.
- NVIDIA GPU operator for K8s does not officially support Amazon Linux*, so the GPU operator does not work well.
  - See [NVIDIA/gpu-operator/issues/227](https://github.com/NVIDIA/gpu-operator/issues/227).
    - *"Amazon Linux is not supported by the GPU Operator, and there are no published driver images"*
    - `daemonset.apps/nvidia-driver-daemonset` fails with *"nvcr.io/nvidia/driver:525.105.17-amzn2: not found"*
    - You can't even configure the tags for `nvcr.io/nvidia/driver`, since the GPU operator enforces the automatic OS distribution loads to define the tag.
    - You can't even update the tags manually, since the `centos7` and `ubuntu20.04` tags do not work on AL2.
    - EKS can simply push NVIDIA driver updates to its AL2 AMIs, so they may not care about the GPU operator.
    - For Lepton, GPU workloads need the first-class support, so we need this GPU operator `nvidia-driver-daemonset` in order to keep the driver up-to-date.
  - We should keep this as an option, in case Ubuntu GPU AMI does not work.
- AL2 is based off Red Hat Enterprise Linux + Centos, which can make it harder to migrate to other cloud providers.
- EVen worse, the `cluster-autoscaler` does not work, when GPU operator is broken.
  - See [lepton/issues/526](https://github.com/leptonai/lepton/issues/526).
  - The `cluster-autoscaler` is unable to scale down AL2 based GPU nodes.

## Official Ubuntu EKS AMI

The official Ubuntu 20.04 AMI for EKS nodes. The official AMIs can be found at [`cloud-images.ubuntu.com`](https://cloud-images.ubuntu.com/docs/aws/eks) or in the SSM parameter store:

```bash
aws ssm get-parameters \
--region us-east-1 \
--names /aws/service/canonical/ubuntu/eks/20.04/1.26/stable/current/amd64/hvm/ebs-gp2/ami-id
```

**Pros**:

- Canonical maintains the AMI, thus no work required on Lepton side.
- EKS managed node group supports custom AMIs, so existing Ubuntu AMI will work.
- First class GPU support from NVIDIA.
- Other GPU providers will support Ubuntu as a first-class citizen.
- The `cluster-autoscaler` works.
  - See [lepton/issues/526](https://github.com/leptonai/lepton/issues/526).

**Cons**:

- No official support from EKS.
- No GPU AMI.
- Needs manual AMI update for new Kubernetes versions.
- Issues `snap` package manager in old Ubuntu AMIs.
  - *error: snap "kubelet-eks" has "auto-refresh" change in progres*
  - [launchpad/cloud-images/2023284](https://bugs.launchpad.net/cloud-images/+bug/2023284)
  - [launchpad/cloud-images/2012689](https://bugs.launchpad.net/cloud-images/+bug/2012689)
- Build script is not open sourced.
- The default image does not cache Lepton-specific container images at the AMI layer.

## Custom Ubuntu AMI built from scratch

We may want to build our AMI from scratch, but it requires a lot of work, as Canonical does not open source their AMI build script.

## Custom Ubuntu AMI (built on top of Ubuntu EKS AMI)

We can address above issues by rebuilding a new AMI on top of the Ubuntu EKS AMI. For GPU support, we can simply take the existing Ubuntu EKS AMI and install the NVIDIA drivers and toolkit. And the snap kubelet-eks issue was just resolved with the latest AMI, but in the worst case, we can always fall back to AL2 node groups. For Lepton specific container images, we can pre-fetch the container images during AMI build process. For upgrade issues, we will build more reliable testing suites to make sure of its release quality. Most important, **we got this working** and confirmed that the GPU operator runs with no issue on the custom Ubuntu AMIs.

See the following links for more discussion:

- [lepton/issues/526](https://github.com/leptonai/lepton/issues/526)
- [lepton/pull/705](https://github.com/leptonai/lepton/pull/705)

And this is an example command to build a custom Ubuntu AMI using [`machine-rs`](../../../machine-rs). See [README.amis.md](./RELEASE.amis.md).

And this is an example output of working GPU operator:

```bash
$ kubectl -n gpu-operator get all

NAME                                                             READY   STATUS      RESTARTS   AGE
pod/gpu-feature-discovery-mcmb4                                  1/1     Running     0          5m30s
pod/gpu-feature-discovery-rfjnp                                  1/1     Running     0          5m30s
pod/gpu-operator-7cfc9fb796-95l55                                1/1     Running     0          5m48s
pod/gpu-operator-node-feature-discovery-master-7bc679897-s46d6   1/1     Running     0          5m48s
pod/gpu-operator-node-feature-discovery-worker-b9j8g             1/1     Running     0          5m48s
pod/gpu-operator-node-feature-discovery-worker-csgq6             1/1     Running     0          5m48s
pod/gpu-operator-node-feature-discovery-worker-fk77g             1/1     Running     0          5m48s
pod/gpu-operator-node-feature-discovery-worker-g85qm             1/1     Running     0          5m48s
pod/gpu-operator-node-feature-discovery-worker-vmtdc             1/1     Running     0          5m48s
pod/nvidia-container-toolkit-daemonset-68vvp                     1/1     Running     0          5m30s
pod/nvidia-container-toolkit-daemonset-6nbxv                     1/1     Running     0          5m30s
pod/nvidia-cuda-validator-9zr76                                  0/1     Completed   0          3m44s
pod/nvidia-cuda-validator-fkw8h                                  0/1     Completed   0          3m40s
pod/nvidia-dcgm-exporter-6vwzp                                   1/1     Running     0          5m30s
pod/nvidia-dcgm-exporter-l9khb                                   1/1     Running     0          5m30s
pod/nvidia-device-plugin-daemonset-gtcpb                         1/1     Running     0          5m30s
pod/nvidia-device-plugin-daemonset-lhkvs                         1/1     Running     0          5m30s
pod/nvidia-device-plugin-validator-bpd4m                         0/1     Completed   0          2m28s
pod/nvidia-device-plugin-validator-z5qnw                         0/1     Completed   0          3m
pod/nvidia-operator-validator-2qsjh                              1/1     Running     0          5m30s
pod/nvidia-operator-validator-dt2z5                              1/1     Running     0          5m30s
```

```bash
$ kubectl -n gpu-operator logs pod/nvidia-device-plugin-daemonset-gtcpb

Defaulted container "nvidia-device-plugin" out of: nvidia-device-plugin, toolkit-validation (init)
NVIDIA_DRIVER_ROOT=/
CONTAINER_DRIVER_ROOT=/host
Starting nvidia-device-plugin
I0624 10:01:18.772290       1 main.go:154] Starting FS watcher.
I0624 10:01:18.772447       1 main.go:161] Starting OS watcher.
I0624 10:01:18.772779       1 main.go:176] Starting Plugins.
I0624 10:01:18.772794       1 main.go:234] Loading configuration.
I0624 10:01:18.772987       1 main.go:242] Updating config with default resource matching patterns.
I0624 10:01:18.773176       1 main.go:253] 
Running with config:
{
  "version": "v1",
  "flags": {
    "migStrategy": "single",
    "failOnInitError": true,
    "nvidiaDriverRoot": "/",
    "gdsEnabled": false,
    "mofedEnabled": false,
    "plugin": {
      "passDeviceSpecs": true,
      "deviceListStrategy": [
        "envvar"
      ],
      "deviceIDStrategy": "uuid",
      "cdiAnnotationPrefix": "cdi.k8s.io/",
      "nvidiaCTKPath": "/usr/bin/nvidia-ctk",
      "containerDriverRoot": "/host"
    }
  },
  "resources": {
    "gpus": [
      {
        "pattern": "*",
        "name": "nvidia.com/gpu"
      }
    ],
    "mig": [
      {
        "pattern": "*",
        "name": "nvidia.com/gpu"
      }
    ]
  },
  "sharing": {
    "timeSlicing": {}
  }
}
I0624 10:01:18.773185       1 main.go:256] Retreiving plugins.
I0624 10:01:18.773620       1 factory.go:107] Detected NVML platform: found NVML library
I0624 10:01:18.773657       1 factory.go:107] Detected non-Tegra platform: /sys/devices/soc0/family file not found
I0624 10:01:18.797269       1 server.go:165] Starting GRPC server for 'nvidia.com/gpu'
I0624 10:01:18.797635       1 server.go:117] Starting to serve 'nvidia.com/gpu' on /var/lib/kubelet/device-plugins/nvidia-gpu.sock
I0624 10:01:18.800073       1 server.go:125] Registered device plugin for 'nvidia.com/gpu' with Kubelet
```

And `cluster-autoscaler` works:

```logs
I0624 20:42:30.904516       1 pre_filtering_processor.go:67] Skipping ip-10-0-2-252.ec2.internal - node group min size reached (current: 1, min: 1)
I0624 20:42:30.904559       1 klogx.go:87] Node ip-10-0-2-185.ec2.internal - nvidia.com/gpu utilization 0.000000
I0624 20:42:30.904631       1 eligibility.go:102] Scale-down calculation: ignoring 1 nodes unremovable in the last 5m0s
I0624 20:42:30.904668       1 cluster.go:155] ip-10-0-2-185.ec2.internal for removal
I0624 20:42:30.904946       1 klogx.go:87] Pod prometheus/prometheus-pushgateway-6ffb6f7466-bfl5l can be moved to ip-10-0-2-252.ec2.internal
I0624 20:42:30.905008       1 klogx.go:87] Pod kube-system/coredns-55fb5d545d-tqnxm can be moved to ip-10-0-1-55.ec2.internal
I0624 20:42:30.905398       1 binder.go:892] "All bound volumes for pod match with node" pod="grafana/grafana-d6bc8f9-phs2m" node="ip-10-0-2-252.ec2.internal"
I0624 20:42:30.905425       1 klogx.go:87] Pod grafana/grafana-d6bc8f9-phs2m can be moved to ip-10-0-2-252.ec2.internal
I0624 20:42:30.906968       1 klogx.go:87] Pod kube-system/coredns-55fb5d545d-zn54w can be moved to ip-10-0-1-55.ec2.internal
I0624 20:42:30.906992       1 cluster.go:178] node ip-10-0-2-185.ec2.internal may be removed
I0624 20:42:30.907001       1 nodes.go:84] ip-10-0-2-185.ec2.internal is unneeded since 2023-06-24 20:38:45.129539464 +0000 UTC m=+318.403015344 duration 3m45.769776521s
I0624 20:42:30.907053       1 static_autoscaler.go:623] Scale down status: lastScaleUpTime=2023-06-24 19:33:31.329619534 +0000 UTC m=-3595.396904579 lastScaleDownDeleteTime=2023-06-24 19:33:31.329619534 +0000 UTC m=-3595.396904579 lastScaleDownFailTime=2023-06-24 19:33:31.329619534 +0000 UTC m=-3595.396904579 scaleDownForbidden=false scaleDownInCooldown=false
I0624 20:42:30.907084       1 static_autoscaler.go:632] Starting scale down
...
I0624 20:45:52.480946       1 klogx.go:87] Pod grafana/grafana-d6bc8f9-phs2m can be moved to ip-10-0-2-252.ec2.internal
I0624 20:45:52.480994       1 klogx.go:87] Pod kube-system/coredns-55fb5d545d-zn54w can be moved to ip-10-0-1-55.ec2.internal
I0624 20:45:52.481026       1 klogx.go:87] Pod prometheus/prometheus-pushgateway-6ffb6f7466-bfl5l can be moved to ip-10-0-2-252.ec2.internal
I0624 20:45:52.481044       1 cluster.go:178] node ip-10-0-2-185.ec2.internal may be removed
I0624 20:45:52.503388       1 taints.go:162] Successfully added ToBeDeletedTaint on node ip-10-0-2-185.ec2.internal
I0624 20:45:52.503536       1 actuator.go:211] Scale-down: removing node ip-10-0-2-185.ec2.internal, utilization: {0 0 0 nvidia.com/gpu 0}, pods to reschedule: coredns-55fb5d545d-tqnxm,grafana-d6bc8f9-phs2m,coredns-55fb5d545d-zn54w,prometheus-pushgateway-6ffb6f7466-bfl5l
```
