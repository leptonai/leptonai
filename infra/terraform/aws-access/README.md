# aws-access

Defines AWS access management via Terraform.

- All prod access states are stored in Terraform cloud -- **do not change manually**.
- DEV account creation predates our Terraform cloud integration, so currently not managed by Terraform.
  - Use [`DEV.tfvars`](./DEV.tfvars) for reference or disaster recovery.

## Update prod account

Make sure to use the same Terraform workspace name!

```bash
cd ./infra/terraform/aws-access
TF_WORKSPACE="aws-access-prod" \
TF_API_TOKEN="REDACTED" \
ENVIRONMENT="PROD" \
./install.sh
```
