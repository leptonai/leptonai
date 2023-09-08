# eks-mothership

## Production

### Step 1. Check the release branch

```bash
# create a release branch
git checkout main
git checkout -B release-0.7.0.20230804
git push origin release-0.7.0.20230804

# sync main to release branch
git checkout main
git pull origin main
git push -f origin main:release-0.7.0.20230804
```

### Step 2. Create mothership EKS cluster itself

Make sure to be logged into our prod account `720771144610`:

```bash
aws sts get-caller-identity
```

```json
{
    "UserId": "720771144610",
    "Account": "720771144610",
    "Arn": "arn:aws:iam::720771144610:..."
}
```

And run the following command:

```bash
# API_TOKEN: ask xiang/cong/gyuho
# TF_API_TOKEN: ask xiang/cong/gyuho

cd ./infra./terraform/eks-mothership
DEPLOYMENT_ENVIRONMENT=PROD \
REGION=us-west-2 \
CHECK_TERRAFORM_APPLY_OUTPUT=false \
API_TOKEN_KEY=mothership_api_token \
API_TOKEN=REDACTED \
TF_API_TOKEN="REDACTED" \
CLUSTER_NAME="mothership-prod-aws-us-west-2" \
MOTHERSHIP_ROLE_NAME="mothership-role" \
./install.sh
```

All variables are defined in [`deployment-environments/PROD.tfvars`](./deployment-environments/PROD.tfvars).

### Step 3. Check mothership status

Once the install command above is complete, check the mothership API:

```bash
# API_TOKEN: use the same value as the one used in mothership install.sh

go install -v ./mothership/cmd/mothership
mothership clusters list -h

mothership clusters list \
--mothership-url https://mothership.app.lepton.ai/api/v1 \
--token ${API_TOKEN}
```

And make sure the cluster name to create would not be in conflict (if any).

### Step 4. Create a new eks-lepton cluster

Checklist:

- Set the right region (us-west-2 for PROD)
- Ubuntu AMIs must be available for the region
- Subscribe "Kubecost - Amazon EKS cost monitoring" in AWS Marketplace (free)

```bash
mothership clusters create \
--mothership-url https://mothership.app.lepton.ai/api/v1 \
--token ${API_TOKEN} \
--region us-west-2 \
--cluster-name ${CLUSTER_NAME} \
--deployment-environment PROD

# to update
mothership clusters update \
--mothership-url https://mothership.app.lepton.ai/api/v1 \
--token ${API_TOKEN} \
--cluster-name ${CLUSTER_NAME} \
--deployment-environment PROD \
--git-ref release-0.7.0.20230804
```

### Step 5. Check the logs

```bash
mothership clusters logs \
--mothership-url https://mothership.app.lepton.ai/api/v1 \
--token ${API_TOKEN} \
--cluster-name ${CLUSTER_NAME}
```
