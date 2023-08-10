(The implementation is still WIP)
### Architecture
The lepton.ai root domain is registered via namecheap. And {cloud|app}.lepton.ai domains are managed by AWS Route 53; traffic
is then routed to ALB. For most tenants, they share a single ALB and requests are routed by our own loadbalancer deployment gloo-edge.
For tenants requesting for dedicated ALB, their requests are routed to the services from a dedicated ALB instance.

### URL structure 
URL: <workspace-name>.<cluster-alias/name>.<env>.lepton.ai

- cluster-alias is the subdomain name provided during cluster creation; it defaults to the cluster-name

examples:
- testws.testcl01.cloud.lepton.ai
- stable.abc.app.lepton.ai

