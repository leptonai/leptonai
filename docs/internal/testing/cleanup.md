## What if my cluster e2e test fails?

We create a new EKS cluster for the e2e test. When a cluster e2e test fails unexpectedly, it may leave cloud resources behind and cause unnecessary spending.

When you encounter a failing cluster e2e test:

- Run `mothership clusters list` to check the status of your cluster.

- If the cluster is not listed, you are good to go.

- If the cluster is present in the list, try to delete it with `mothership clusters delete -c <name>`.

- Simultaneously, log into the development AWS account and navigate to the EKS tab. Locate the failed cluster and manually remove the node groups. This step will help us reduce spending immediately.