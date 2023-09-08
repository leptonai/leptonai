# Workspace updates caused service mapping errors for old deployments

### Date

8/25/2023

### Authors

Cong Ding

### Summary

We updated the labels of user deployments, which caused service mapping errors and failed the network of user deployments.

### Impact

Customers are not able to access their deployments via the public endpoint.

### Timeline

- 5/18/2023 Merged the PR and cherry-picked it to the release branch
- 5/19/2023 We updated prod workspaces with the new release image
- 5/20/2023 We found that customers were not able to access their endpoints
- 5/20/2023 Manually deleted deployments to mitigate the issue

### Root Causes

We tried to modify the immutable field spec.selector in deployments, which failed, so the deployments were not updated. However,
the selector field in service was mutable and successfully updated. As a result, the service could not find the deployment and pods.

### Resolution

We manually deleted deployments, so the labels and selectors were updated.

### Action Items

- Fix the operator to control each mutable field and not to blindly update resources.
- In the future, we should run upgrade tests before deploying release versions to prod
