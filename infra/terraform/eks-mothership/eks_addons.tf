module "eks_blueprints_kubernetes_addons" {
  source = "github.com/aws-ia/terraform-aws-eks-blueprints-addons?ref=ac7fd74d9df282ce6f8d068c4fd17ccd5638ae3a"

  cluster_name     = module.eks.cluster_name
  cluster_endpoint = module.eks.cluster_endpoint
  cluster_version  = module.eks.cluster_version

  oidc_provider     = module.eks.cluster_oidc_issuer_url
  oidc_provider_arn = module.eks.oidc_provider_arn

  # https://github.com/kubernetes-sigs/external-dns/releases
  enable_external_dns = true
  external_dns = {
    name = "external-dns"

    # https://github.com/kubernetes-sigs/external-dns/releases
    chart_version = "1.13.0"

    repository = "https://kubernetes-sigs.github.io/external-dns/"
    namespace  = "external-dns"

    # https://github.com/aws-ia/terraform-aws-eks-blueprints-addons/blob/main/main.tf
    create_policy = true
    create_role   = true

    # https://github.com/kubernetes-sigs/external-dns/blob/master/charts/external-dns/values.yaml
    # https://github.com/kubernetes-sigs/external-dns/blob/master/pkg/apis/externaldns/types.go
    values = [yamlencode({
      # default is "upsert-only" -- DNS records will not get deleted even when the Ingress resources are deleted
      # "sync" ensures when ingress resource is deleted, the corresponding DNS record in Route53 gets deleted
      # TODO: these creates a lot of dangling DNS records, use "sync" once we figure out
      # https://github.com/kubernetes-sigs/external-dns/issues/2674
      policy : "sync"

      # When using the TXT registry, a name that identifies this instance of ExternalDNS
      # (default: default)
      #
      # NOTE: this is used for filtering records based on the txt owner id
      # NOTE: we do not need "domainFilters" with "${module.eks.cluster_name}.cloud.lepton.ai"
      txtOwnerId : "${module.eks.cluster_name}"

      serviceAccount = {
        create = true
      }
      rbac = {
        create = true
      }
    })]

    oidc_providers = {
      main = {
        provider_arn               = module.eks.oidc_provider_arn
        namespace_service_accounts = ["external-dns:external-dns-sa"]
      }
    }
  }
  external_dns_route53_zone_arns = [
    "arn:aws:route53:::hostedzone/${var.lepton_cloud_route53_zone_id}"
  ]
}
