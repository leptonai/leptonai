
# Metrics not available, missing metering data (incident #003)

### Date

2023-08-09

### Authors

[@gyuho](http://github.com/gyuho), [@awliu2](http://github.com/awliu2)

### Summary

Default EKS kubecost add-on relies on the prometheus server pod with an availability-zone specific volume. Which cannot be moved/remapped to another node in a different zone in case of node failure/replacement. As a result, the prometheus server pod was stuck in the "pending" state and the kubecost pod was not working.

### Impact

Internal metrics and metering data were either missing or not available.

### Timeline

- 2023-08-09: noticed the kubecost pods are not working ([link](https://leptonai.slack.com/archives/C05AWUGS57Y/p1691533186237379))
- 2023-08-09: identified that "cost-analyzer" pod is not working because it cannot query against "pending" state prometheus server
- 2023-08-09: identified that "prometheus-server" pod is pending due to "1 node(s) had volume node affinity conflict"
- 2023-08-09: deleted PVC and pod to retrigger the volume provisioning (resolved)
- 2023-08-09: first fix attempt by moving PVC-based prometheus server deployment to ephemeral volume ([PR](https://github.com/leptonai/lepton/pull/2395)) for kube-prometheus-stack
- 2023-08-10: same issue happened to DEV eks-lepton cluster
- 2023-08-10: resolved with the same workarounds
- 2023-08-11: second fix attempt by moving PVC-based prometheus server deployment to emptyDir + custom helm chart ([PR](https://github.com/leptonai/lepton/pull/2466)) for kubecost

### Root Causes

A series of node scale ups and downs replaces the node that the prometheus pod was assigned to. And the new node was launched in a different availability zone. The prometheus pod was stuck in the "pending" state because the PVC was bound to the old node and the new node cannot be assigned to the PVC.

### Resolution

Manually deleting the PVC and the pod retriggered the volume provisioning. And the prometheus pod was assigned to the new node in the new availability zone with the new volume. See the [github issue](https://github.com/leptonai/lepton/issues/2434) for detailed workflow. The first fix was to [move kube-prometheus-stack to use ephemeral storage](https://github.com/leptonai/lepton/pull/2395). The second fix was to [move kubecost to use emptyDir](https://github.com/leptonai/lepton/pull/2466).

### Detection

The product team found out metering data were missing, and the platform team manually inspect the kubecost deployment and found out the prometheus pod was stuck in the "pending" state.

### Action Items

- Redeploy eks-lepton with all the prometheus server deployment fixes.
- Alert when the prometheus server pod is not running (see [issue](https://github.com/leptonai/lepton/issues/2424)).
- Alert when the kubecost cost-analyzer pod is not running (see [issue](https://github.com/leptonai/lepton/issues/2424)).
- Alert when the metering job fails to run (see [issue](https://github.com/leptonai/lepton/issues/2424)).

### Lessons Learned

#### What went well

We quickly identified the root cause and resolved the issue with quick workarounds. We also made and tested permanent fixes within a day.

#### What went wrong

There was no alert when the metering data or metrics were missing. The fixes were made shortly, and took days to test and deploy.
