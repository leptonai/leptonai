# Kubecost Prometheus Pod Down following cluster upgrade (incident 4)

### Date 
8/22/23

### Author
Andi Liu 

### Summary
The `kubecost-prometheus-server` pod in `kubecost-cost-analyzer` namespace was unavailable/down for around 3 days starting from 8/18/23 around 4 PM PST, and rectified on 8/21/23 around 10 AM PST. This incident affected the `prod01awsuswest2` cluster.

```
k -n kubecost-cost-analyzer describe pod/kubecost-prometheus-server-7b9759bdfd-qz29f
Events:
  Type     Reason   Age                      From     Message
  ----     ------   ----                     ----     -------
  Warning  BackOff  75s (x18319 over 2d20h)  kubelet  Back-off restarting failed container prometheus-server in pod kubecost-prometheus-server-7b9759bdfd-qz29f_kubecost-cost-analyzer(e1856b53-cd8c-4c86-9f48-5d0b56b5cfc0)
```

### Impact
Without `kubecost-prometheus-server`, the kubecost app was unable to gather various metrics, including pod labels. This led to all metering data gathered from `prod01awsuswest2` missing information for the deployment name and shape, and ultimately meant that none of the data from this period could be used for billing purposes.

### Timeline
- 8/18/23, afternoon PST: 0.8.0 release is pushed to production cluster `prod01uswest2`.
- 8/18/23, ~4:00 PM PST: `kubecost-prometheus-server` sees a spike in memory usage, exceeds its limits, and is killed by the OOM killer. The pod is restarted. 
- 8/21/23, 8 AM PST: @yuze notices billing values for promptai workspace does not seem to be correct. [(issue 2717)](https://github.com/leptonai/lepton/issues/2717)
- 8/21/23, morning: discover that `kubecost-prometheus-server` pod is down, and has been down for 3 days, initial issue was an OOM kill.
- 8/21/23, morning: increased memory limits for `kubecost-prometheus-server` pod to 8GB, and requests to 4 GB, and restarted the pod. This fixes the issue.
- 8/22/23: @xiang finds that around 3:30 PM PST on 8/18/23, there was a memory spike for `kubecost-prometheus-server` likely occuring during cluster upgrade.

### Root Causes
See above; memory spike during cluster upgrade caused OOM kill, and pod was unable to restart afterwards.

[Prometheus docs](https://prometheus.io/docs/prometheus/1.8/storage/#memory-usage) state that "default value of `storage.local.target-heap-size` is 2GiB and thus tailored to 3GiB of physical memory usage", however we had set the memory request to 2 GiB, and the limit to 3 GiB. Thus under heavy load our resource configuration was insufficient for the prometheus pod to run.

### Resolution
Increase memory request from 2 Gi to 4 Gi, limit from 3 Gi to 6 Gi: [(PR 2753)](https://github.com/leptonai/lepton/pull/2753/files).

### Detection
Manual detection by @yuze, @xiang, and @andi. 

### Action Items
* Add monitoring and alerting for all metering related operations, applications, and services, including the deployments in the `kubecost-cost-analyzer` namespace: [(Issue #2724)](https://github.com/leptonai/lepton/issues/2724)

#### What went wrong
* no metering monitoring at all meant that the issue was not detected for multiple days.
