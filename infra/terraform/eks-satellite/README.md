
# eks-satellite

This module creates AWS resources for satellite nodes.

## Create satellite node resources

Make sure to use the same Terraform workspace name!

```bash
cd ./infra/terraform/eks-satellite
CLUSTER_NAME="mycluster" \
SATELLITE_NAME="mysatellite" \
TF_API_TOKEN=REDACTED \
ENVIRONMENT="DEV" \
./install.sh
```
