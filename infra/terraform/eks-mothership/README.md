# eks-mothership

For production, run the following command:

```bash
cd ./infra./terraform/eks-mothership

DEPLOYMENT_ENVIRONMENT=PROD \
REGION=us-west-2 \
ENABLE_COPY_LEPTON_CHARTS=true \
CHECK_TERRAFORM_APPLY_OUTPUT=false \
API_TOKEN=123 \
TF_API_TOKEN="..." \
CLUSTER_NAME="mothership-prod-aws-us-west-2" \
./install.sh mothership-prod-aws-us-west-2
```

All variables are defined in [`deployment-environments/PROD.tfvars`](./deployment-environments/PROD.tfvars).
