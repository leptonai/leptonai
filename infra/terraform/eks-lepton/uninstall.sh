#!/bin/bash

set -x

# List of Terraform modules/resources to destroy in sequence (reverse order of apply)
# need to delete existing kubernetes resources to avoid dependency conflicts
#
# NOTE
# s3/roles can be deleted at the end since it does not cause any conflicts
#
# NOTE
# "aws_acm_certificate" depends on the EKS cluster load balancer
# so we need to delete the EKS cluster first
targets=(
  "null_resource.delete_all_lepton_deployments_and_ingresses"
  "helm_release.lepton_crd"
  "helm_release.lepton"

  # bug https://github.com/tigera/operator/issues/2031
  "null_resource.delete_calico_installation"

  "helm_release.kube_prometheus_stack"
  "helm_release.gloo_edge"
)

if [ -z "$CLUSTER_NAME" ]; then
  CLUSTER_NAME=$(terraform output -json | jq -r '.cluster_name.value')
fi

if [ -z "$SHARED_ALB_MAIN_DOMAIN" ]; then
  SHARED_ALB_MAIN_DOMAIN=$(terraform output -json | jq -r '.shared_alb_main_domain.value')
fi

if [ -z "$SHARED_ALB_ROUTE53_ZONE_ID" ]; then
  SHARED_ALB_ROUTE53_ZONE_ID=$(terraform output -json | jq -r '.shared_alb_route53_zone_id.value')
fi

if [[ -z $TF_API_TOKEN ]]; then
  echo "ERROR: Terraform Cloud API token not specified"
  exit 1
fi

if [[ -z $TF_WORKSPACE ]]; then
  export TF_WORKSPACE="cl-$CLUSTER_NAME-default"
else
  export TF_WORKSPACE
fi
export TF_TOKEN_app_terraform_io=$TF_API_TOKEN

if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" == "null" ]; then
  echo "ERROR: Cluster name not specified"
  exit 1
fi

if [ -z "$SHARED_ALB_MAIN_DOMAIN" ] || [ "$SHARED_ALB_MAIN_DOMAIN" == "null" ]; then
  echo "ERROR: SHARED_ALB_MAIN_DOMAIN not specified"
  exit 1
fi
if [ -z "$SHARED_ALB_ROUTE53_ZONE_ID" ] || [ "$SHARED_ALB_ROUTE53_ZONE_ID" == "null" ]; then
  echo "ERROR: SHARED_ALB_ROUTE53_ZONE_ID not specified"
  exit 1
fi

# here, we assume the running script or mothership(controller)
# copies the whole directory in the same directory tree
ENABLE_COPY_LEPTON_CHARTS=${ENABLE_COPY_LEPTON_CHARTS:-false}
if [[ "$ENABLE_COPY_LEPTON_CHARTS" == "true" ]]; then
  # this is not running via mothership, thus requiring manual copy
  echo "copying eks-lepton charts from ../../../charts"
  rm -rf ./charts && cp -r ../../../charts .
  echo "copying lepton CRDs from ../../../deployment-operator/config/crd/bases"
  cp ../../../deployment-operator/config/crd/bases/*.yaml ./charts/eks-lepton/templates/
else
  echo "skipping copying lepton charts"
fi

if terraform init --upgrade ; then
  echo "SUCCESS: Terraform init completed successfully"
else
  echo "ERROR: Terraform init failed"
  exit 1
fi

# ref. https://developer.hashicorp.com/terraform/cli/config/environment-variables
export TF_LOG="INFO"
export TF_LOG_PATH="tf.uninstall.log"

# force destroy in case terraform plan fails due to CR not found
# e.g., install failed before CRs were created
# ref. https://github.com/leptonai/lepton/issues/2191
DELETE_TF_STATE_NETWORK_POLICY=${DELETE_TF_STATE_NETWORK_POLICY:-false}
if [[ "$DELETE_TF_STATE_NETWORK_POLICY" == "true" ]]; then
  echo "deleting terraform state for network policy resources"
  terraform state rm kubernetes_manifest.allow_user_pod_to_external
  terraform state rm kubernetes_manifest.allow_user_pod_to_kube_dns
  terraform state rm kubernetes_manifest.allow_node_to_all_policy
  terraform state rm kubernetes_manifest.allow_lepton_to_systems_as_dest_policy
  terraform state rm kubernetes_manifest.allow_lepton_to_k8s_service_policy
fi

DEPLOYMENT_ENVIRONMENT=${DEPLOYMENT_ENVIRONMENT:-TEST}
REGION=${REGION:-"us-east-1"}
for target in "${targets[@]}"
do
  echo "deleting ${target}"
  terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" \
    -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" -target="$target" \
    -var="shared_alb_main_domain=$SHARED_ALB_MAIN_DOMAIN" \
    -var="shared_alb_route53_zone_id=$SHARED_ALB_ROUTE53_ZONE_ID"
done

echo "deleting the remaining resources"
if terraform apply -destroy -auto-approve -var-file="deployment-environments/$DEPLOYMENT_ENVIRONMENT.tfvars" \
  -var="region=$REGION" -var="cluster_name=$CLUSTER_NAME" \
  -var="shared_alb_main_domain=$SHARED_ALB_MAIN_DOMAIN" \
  -var="shared_alb_route53_zone_id=$SHARED_ALB_ROUTE53_ZONE_ID" ; then
  echo "SUCCESS: Terraform destroy completed successfully"
else
  echo "FAILED: Terraform destroy failed"
  exit 1
fi

# NOTE: to clean up kubeconfig file used for "local-exec"
# rm -f /tmp/$CLUSTER_NAME.kubeconfig
