## Mothership

The mothership handles all lepton environments and users.

It provisions and manages the compute infrastructure on cloud providers using Kubernetes.

It manages the lepton environment within a namespace of the Kubernetes clusters.

It controls lepton users and their accessibility to each lepton environment.

### The design

We have a single global mothership that operates within a Lepton-controlled EKS cluster. Our goal is to keep the mothership as simple as possible, ensuring it is stateless and fault-tolerant. In the event of a mothership crash, it should not impact any existing Lepton environments or users.

The mothership utilizes Terraform to manage the infrastructure across various cloud providers. It is responsible for managing the Terraform state, ensuring that we maintain control and visibility.

Within the Kubernetes cluster it runs in, the mothership maintains the lepton workspace as a custom resource (CR). Each lepton environment is associated with a Lepton API server and a set of operators that run within a single namespace.

User information is stored in a shared database with the web authentication system. The mothership serves as the exclusive writer to this database, taking responsibility for managing access tokens and maintaining the relationship between users and their respective lepton environments.

### Command-line interface

```bash
go install -v ./mothership/cmd/mothership
mothership -h
```

To use the cli for dev:
1. point .kube/config to the mothership cluster in aws dev account
2. save mother ship context by running `mothership context save -n dev -u https://mothership.cloud.lepton.ai/api/v1 -t <mothership token>`
