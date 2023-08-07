# How does the deployment operator reconcile

The operator watches LeptonDeployment (LD) and all subresources created based on LD. If any of the resources are modified by either the API-server or engineer, it triggers the reconcile function, which checks and updates/recreates the resources with the correct spec.

## Common workflows

### Creation path

The API-server writes LD, which triggers a reconciliation in the operator. The reconcile function reads the LD and, based on the LD, generates the spec of deployment, PV, PVC, service, ingress, etc.

The operator also adds a finalizer to LD to ensure all its subresources are deleted cleanly before LD itself gets deleted.

### Deletion path

The API-server calls to delete the LD. Because of the finalizer, k8s will not immediately deleted the LD. It adds a deletion timestamp. The modification to LD triggers a reconciliation in the operator. The operator sees the deletion timestamp, deletes all the subresources, and then removes the finalizer. K8s will delete the LD once the finalizer is removed.

### Update path

The API-server updates the LD, which triggers a reconciliation. The operator updates all resources based on the new LD.

### Unexpected events

If an engineer manually modifies any subresources, it triggers a reconciliation. The operator will use LD to regenerate the spec of the subresources so the subresources are immediately updated to the desired state.

## Operator actions order

0. Make sure LD is not nil. If it is nil, the LD is deleted so we have nothing to do.

1. Update status.state to one of starting/updating/ready/deleting.

2. Check whether the LD has a deletion timestamp. If it has, the operator does the deletion of subresources.
Note that more subresources have an ownerref of the LD, so the operator need not explicitly delete them because deleting the LD will trigger k8s to delete them. PV does not have the ownerref, so the operator has to explicitly delete it before removing the finalizer of the LD.

3. Check whether the LD has the finalizer. If not, add it.

4. Create or update subresources based on the current LD.

## Testing

How can I test modifying some of the subresources? In our test workspaces, we can first scale the operator deployment to `replica=0`, which disables the operator. Then we modify whatever we want to test. After the test, we can scale the operator deployment back to `replica=1` so the operator can reconcile and revert the manual changes in the subresources.
