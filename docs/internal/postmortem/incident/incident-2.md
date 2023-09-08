# Title (incident #2): CI runners down


### Date

8/11/2023

### Authors

Cong Ding

### Summary

The node that runs GitHub runners had no disk space to start runners, so all CI jobs are pending/failing.

### Root Causes

We used the runners to build docker images with docker in docker. kubelet couldn't clean them up, so disk usage is near 1TB. On 8/7/2023, we increased the max number of concurrent runners, which used more disks, pushed the disk usage to the boundary, and failed everything in the node.

When mitigating the issue by deleting old images, we mistakenly deleted the pause image (a system image), which failed all future image pulling.

### Resolution

We expanded the disk size to 2TB and then replaced the node. We also changed to using GitHub-managed runners to build docker images.

### Detection

Yangqing found that all CI jobs are failing due to disk issues.
In the future, we should monitor disk usage of nodes.
