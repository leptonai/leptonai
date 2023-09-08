# workspace

## Set up mothership context

```bash
MOTHERSHIP_URL="https://mothership.cloud.lepton.ai/api/v1" # for dev
MOTHERSHIP_URL="https://mothership.app.lepton.ai/api/v1" # for prod

MOTHERSHIP_CONTEXT_NAME=""
MOTHERSHIP_TOKEN=""

mothership context save \
--name $MOTHERSHIP_CONTEXT_NAME \
--url $MOTHERSHIP_URL \
--token $MOTHERSHIP_TOKEN

mothership context list
```

## Create workspaces

**DO NOT CREATE MANUALLY.**

Always use `mothership` API to create new workspaces.

```bash
mothership workspaces list

mothership workspaces create \
--cluster-name $CLUSTER_NAME \
--workspace-name $WORKSPACE_NAME \
--description $WORKSPACE_NAME \
--git-ref $GIT_BRANCH_NAME \
--api-token $API_TOKEN

mothership workspaces logs \
--mothership-url $MOTHERSHIP_URL \
--git-ref $GIT_BRANCH_NAME \
--w $WORKSPACE_NAME
```

## Update existing workspaces

**DO NOT UPDATE MANUALLY.**

Always use `mothership` API to manage existing workspaces.

```bash
mothership workspaces list

mothership workspaces update \
--workspace-name $WORKSPACE_NAME \
--git-ref $GIT_BRANCH_NAME \
--image-tag $IMAGE_TAG

mothership workspaces logs \
--w $WORKSPACE_NAME
```
