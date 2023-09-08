## Networking Policy

[networking policy definitions](https://github.com/leptonai/lepton/blob/main/infra/terraform/eks-lepton/network_policy.tf)

### Do not allow direct communication between user workloads.

We only allow access to user workloads through the service ingress, where we enforce access with token protection. In the future, we may consider allowing selective direct communication between workloads that belong to the same workspace.

### Allow external internet communication for user workloads.

User workloads can freely access the external internet without any restrictions. We also provide DNS service for naming resolution.

### Allow unrestricted access for all Lepton system components.

Lepton system components are trusted workloads that can communicate with each other without any networking level (L4) restrictions. System components include node agents such as Kubelet, which need to access user workloads for health checking.
