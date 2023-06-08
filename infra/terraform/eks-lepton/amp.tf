#------------------------------------------
# Amazon Prometheus
#------------------------------------------
locals {
  amp_ingest_service_account = "amp-iamproxy-ingest-service-account"
  namespace                  = "prometheus"
}

resource "aws_prometheus_workspace" "amp" {
  alias = format("%s-%s", "amp-ws", local.cluster_name)
}

#---------------------------------------------------------------
# IRSA for VPC CNI
#---------------------------------------------------------------
module "amp_ingest_irsa" {
  source    = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version   = "~> 5.14"
  role_name = format("%s-%s", local.cluster_name, "amp-ingest")

  attach_amazon_managed_service_prometheus_policy  = true
  amazon_managed_service_prometheus_workspace_arns = [aws_prometheus_workspace.amp.arn]

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["${local.namespace}:${local.amp_ingest_service_account}"]
    }
  }
}
