## Changing Resource Quota

The default resource quota for a workspace is 4 CPUs, 16 GB of memory, and 1 GPU. The actual setting is slightly higher than this since we reserve 1 CPU and 1 GB for system overhead (current usage is under 150m CPU and 256MB memory).

To change this default setting, follow the steps below to modify the Resource Quota of the corresponding Kubernetes namespace.

1. Create a YAML file named quota.yaml and save it with the following content:

```
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota-myworkspace
  namespace: myworkspace
spec:
  hard:
    requests.cpu: "16"
    requests.memory: 128Gi
    requests.nvidia.com/gpu: "4"
```

2. Apply the change using kubectl:
Before proceeding, ensure that you have the necessary access to the Kubernetes Cluster running this workspace.

```
kubectl apply -f quota.yaml
```

3. Verify the quota change:

```
kubectl describe resourcequota quota-myworkspace -n myworkspace
```

Make sure to replace quota-myworkspace with the actual name of the resource quota you specified in the YAML file and myworkspace with the target namespace.

The command will provide detailed information about the updated resource quota, confirming the changes you made.
