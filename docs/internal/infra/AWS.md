## Quota

Everything listed below is per region.

1 customer translates to the following:

```text
EKS: 1/10
VPC: 1
NAT GATEWAY: 3 (1 per AZ)
ALB: 1
EIP: 4

CPUs: 10 vCPUs
MEMORY: 100 GB
== 1/6 m6a.16xlarge

GPUs: 10 vCPUs
MEMORY: 20 GB
== 1 g4dn.xlarge + 1 g5.2xlarge
```

100 customers translate to the following quota:

```text
EKS (L-1194D53C): 10
VPC (L-F678F1CE): 20
NAT GATEWAY (L-FE5A380F): 60 (20 per AZ)
ALB (L-53DA6B97): 100
EIP (L-0263D0A3): 500

Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances (L-1216C47A):
1024 (# of vCPUs)

Running On-Demand G and VT instances (L-DB2E81BA):
1024 (# of vCPUs)
# OR
g4dn.xlarge (L-CAE24619): 100 (# of hosts)
g5.2xlarge  (L-A6E7FE5E): 100 (# of hosts)

# for whitelisted customers
p4de.24xlarge (L-86A789C3): 5 (# of hosts)
```

See below for more details.

### Compute

#### EKS

O(10). We only need a small number of EKS clusters per region as most of our customers would share one EKS cluster.

### Machines

m6a.16xlarge - O(deployments). This is our default CPU machine type. The minimum number should be set to 25.

gd4n.xlarge - O(deployments).  The minimum number should be set to 25.

g5.2xlarge - O(deployments). The minimum number should be set to 25.

p4de.24xlarge - As per customer request.

### Networking

#### VPC

O(10) per region. We have one VPC per EKS cluster. Most customers share one EKS, thus one VPC.

#### ALB

O(customers). Each customer needs one shared ALB for their control plane access and deployment for its public endpoint.

We will probably improve our load balancing and routing layers and share ALBs for both the control plane and deployments for all customers. Unless a customer explicitly asks for a dedicated IP and load balancer, they will share them with other customers.

#### EIP

O(customers). Each ALB consumes one EIP. The required number of EIP is thus the same as ALB.

### Storage

#### EFS

O(customers). We provision one EFS per customer. The default quota for EFS is 1000, which should be good enough.

#### S3

O(customers) of buckets. We create one bucket per customer to store their photos

#### EBS

O(10). We only use EBS for our system components, not user workloads.

### Others


#### Amazon Managed Prometheus

TODO