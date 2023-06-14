module "eks_blueprints_kubernetes_addons" {
  source = "github.com/aws-ia/terraform-aws-eks-blueprints-addons?ref=ac7fd74d9df282ce6f8d068c4fd17ccd5638ae3a"

  cluster_name     = module.eks.cluster_name
  cluster_endpoint = module.eks.cluster_endpoint
  cluster_version  = module.eks.cluster_version

  oidc_provider     = module.eks.cluster_oidc_issuer_url
  oidc_provider_arn = module.eks.oidc_provider_arn

  eks_addons = {
    aws-ebs-csi-driver = {
      service_account_role_arn = module.ebs_csi_driver_irsa.iam_role_arn
    }
  }

  enable_cluster_autoscaler = true

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
      txtOwnerId : "${module.eks.cluster_name}"

      # Limit possible target zones by a domain suffix; specify multiple times for multiple domains (optional)
      # make ExternalDNS see only the hosted zones matching provided domain, omit to process all available hosted zones
      domainFilters : [
        "${module.eks.cluster_name}.cloud.lepton.ai"
      ]

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

  #---------------------------------------------------------------
  # Prometheus Add-on
  #---------------------------------------------------------------
  # TODO: this has been removed in https://github.com/aws-ia/terraform-aws-eks-blueprints-addons/blob/main/variables.tf
  enable_prometheus = true
  # https://prometheus.io/docs/prometheus/latest/configuration/configuration/
  # https://prometheus.io/docs/prometheus/latest/storage/
  # https://github.com/prometheus-community/helm-charts/blob/main/charts/prometheus/values.yaml
  prometheus_helm_config = {
    values = [yamlencode({
      server : {
        global : {
          scrape_interval : "5s"
          scrape_timeout : "4s"
        }
        extraFlags : [
          "storage.tsdb.wal-compression"
        ]
        persistentVolume : {
          enabled : true
          mountPath : "/data"
          size : "8Gi"
          storageClass : "gp3"
        }
      }
      extraScrapeConfigs = <<EOT
- job_name: lepton-deployment-pods
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_photon_id]
    action: keep
    regex: .+
  - source_labels: [__meta_kubernetes_pod_label_lepton_deployment_id]
    action: keep
    regex: .+
  - action: replace
    source_labels: [__meta_kubernetes_pod_label_photon_id]
    target_label: kubernetes_pod_label_photon_id
  - action: replace
    source_labels: [__meta_kubernetes_pod_label_lepton_deployment_id]
    target_label: kubernetes_pod_label_lepton_deployment_id
  - action: replace
    source_labels: [__meta_kubernetes_pod_name]
    target_label: kubernetes_pod_name
  - action: replace
    source_labels: [__meta_kubernetes_namespace]
    target_label: kubernetes_namespace
EOT
    })]
  }

  enable_amazon_prometheus             = true
  amazon_prometheus_workspace_endpoint = aws_prometheus_workspace.amp.prometheus_endpoint

  enable_grafana = true
  grafana_helm_config = {
    create_irsa = true # Creates IAM Role with trust policy, default IAM policy and adds service account annotation
    set_sensitive = [
      {
        name  = "adminPassword"
        value = "admin888"
      }
    ]
  }

  enable_efs_csi_driver = true
}
