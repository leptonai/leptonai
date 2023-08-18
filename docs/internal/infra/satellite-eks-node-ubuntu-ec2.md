# Sattelite EKS node using Ubuntu EC2

**THIS IS EXPERIMENTAL.**

TODO

## Goals

- On-prem node running outside of VPC can be authorized to join the EKS cluster.
- The node can be stably running sending heartbeats to the EKS cluster.
- The node can run a pod(s).
- The node can run Kubernetes deployments with services, using Node IP.

## Non-goals

- GPU workloads.

## Prerequisites

- EC2 instance with Ubuntu 20.04 or 22.04, outside of EKS cluster VPC
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

TODO
