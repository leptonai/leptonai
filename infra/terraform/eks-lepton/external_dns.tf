locals {
  external_dns_namespace = "external-dns"
  external_dns_app_name  = "external-dns"
  external_dns_sa        = "external-dns-sa"
}

resource "kubernetes_namespace" "external_dns" {
  metadata {
    annotations = {
      name = local.external_dns_namespace
    }
    name = local.external_dns_namespace
  }
}

# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md
resource "aws_iam_policy" "external_dns" {
  name        = "${local.cluster_name}-external-dns-policy"
  description = "external-dns IAM policy"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "route53:ChangeResourceRecordSets"
        ],
        "Resource" : [
          "arn:${local.partition}:route53:::hostedzone/${var.lepton_cloud_route53_zone_id}"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "route53:ListHostedZones",
          "route53:ListResourceRecordSets",
          "route53:ListTagsForResource"
        ],
        "Resource" : "*"
      }
    ]
  })
}

resource "aws_iam_role" "external_dns" {
  name = "${local.cluster_name}-external-dns-role"

  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          Federated : "arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
        },
        Action : "sts:AssumeRoleWithWebIdentity",
        Condition : {
          StringEquals : {
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com",
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:${kubernetes_namespace.external_dns.metadata[0].name}:${local.external_dns_sa}"
          }
        }
      }
    ]
  })

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role_policy_attachment" "external_dns" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.external_dns.name}"
  role       = aws_iam_role.external_dns.name

  depends_on = [
    aws_iam_policy.external_dns,
    aws_iam_role.external_dns
  ]
}

# "helm_release.external_dns" creates default service accounts
# but without amazon managed prometheus remote write enabled service accounts
# overwrite here
resource "kubernetes_service_account" "external_dns" {
  metadata {
    name      = local.external_dns_sa
    namespace = kubernetes_namespace.external_dns.metadata[0].name

    labels = {
      "app.kubernetes.io/instance" = local.external_dns_app_name
      "app.kubernetes.io/name"     = local.external_dns_app_name
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.external_dns.name}"
    }
  }

  # destroy an object and recreate it
  # in case of updates
  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.external_dns,
    kubernetes_namespace.external_dns,
  ]
}

# https://github.com/kubernetes-sigs/external-dns
resource "helm_release" "external_dns" {
  name             = local.external_dns_app_name
  namespace        = kubernetes_namespace.external_dns.metadata[0].name
  create_namespace = false

  chart      = "external-dns"
  repository = "https://kubernetes-sigs.github.io/external-dns/"

  # https://github.com/kubernetes-sigs/external-dns/blob/master/charts/external-dns/Chart.yaml
  version = "1.13.0"

  # https://github.com/kubernetes-sigs/external-dns/blob/master/charts/external-dns/values.yaml
  # https://github.com/kubernetes-sigs/external-dns/blob/master/pkg/apis/externaldns/types.go
  values = [yamlencode({
    # default is "upsert-only" -- DNS records will not get deleted even when the Ingress resources are deleted
    # "sync" ensures when ingress resource is deleted, the corresponding DNS record in Route53 gets deleted
    # https://github.com/kubernetes-sigs/external-dns/issues/2674
    policy = "sync"

    # When using the TXT registry, a name that identifies this instance of ExternalDNS
    # (default: default)
    #
    # NOTE: this is used for filtering records based on the txt owner id
    # NOTE: we do not need "domainFilters" with "${module.eks.cluster_name}.cloud.lepton.ai"
    txtOwnerId = "${module.eks.cluster_name}"

    serviceAccount = {
      create = false
      name   = local.external_dns_sa
    }

    rbac = {
      create = true
    }
  })]

  depends_on = [
    kubernetes_service_account.external_dns,
  ]
}
