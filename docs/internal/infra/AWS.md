## Quota

Everything listed below is per region.

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