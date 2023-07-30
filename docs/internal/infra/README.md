# Lepton AI Infra

At a high level, we have Kubernetes clusters, each including multiple Lepton workspaces. Each workspace has an API server, a deployment operator, and an optional web server.

Clusters are an internal concept. Customers only see workspaces.

We have a centralized mothership Kubernetes cluster managing the resources, e.g., creating and updating clusters/workspaces.

## States

We use Terraform to install all resources and use Hashicorp to backup Terraform states.
The terraform state of a Kubernetes cluster is stored in the Hashicorp workspace with the same name.
The state of a Lepton workspace is stored in the Hashicorp workspace with names like `<cluster_name>-<workspace_name>`.

To avoid confusion and conflicts, we require cluster and workspace names not to have `-`, i.e., they must follow `^[a-z][a-z0-9]{0,30}$`

## Mothership

Mothership is created using code in [terraform/eks-mothership](terraform/eks-mothership), under eks `mothership-0`.
[cicd-mothership.yaml](../.github/workflows/cicd-mothership.yaml) automatically bumps its image version (not yet).
We have to manually update other resources using [install.sh](terraform/eks-mothership/install.sh).

## Clusters

Mothership creates and updates clusters using code in [terraform/eks-lepton](terraform/eks-lepton).
We have to call mothership to update cluster-level resources, including CRDs.

The mothership API for creating clusters is at [CRD](../mothership/crd/api/v1alpha1/leptoncluster_types.go).

Currently, we have two clusters: `dev` and `ci`. As their names suggest, we use `dev` for development purposes and `ci` to run continous integrity.
Additionally, `dev` cluster also runs the [github actions runners](../github-actions-runner/).

TODO: we weekly delete and recreate the `ci` cluster.

## Workspaces

Mothership creates and updates workspaces using code in [terraform/workspace](terraform/workspace).

The mothership API for creating workspaces is at [CRD](../mothership/crd/api/v1alpha1/leptonworkspace_types.go).

Currently, we have three long-running workspaces: `latest`, `staging`, and `stable`.
[cicd-satallite.yaml](../.github/workflows/cicd-satallite.yaml) automatically bumps the image version of the workspace named `latest`.
We have to call mothership to update other workspaces.

Feel free to create workspaces in `dev` for testing purposes. Please remember to delete them after testing.

TODO: we require people to specify a TTL when creating/updating a workspace. Expired workspaces will be automatically deleted.
