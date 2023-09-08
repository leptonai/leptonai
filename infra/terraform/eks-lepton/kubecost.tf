locals {
  kubecost_namespace            = "kubecost-cost-analyzer"
  kubecost_app_name             = "kubecost"
  kubecost_sa_prometheus_server = "kubecost-prometheus-server"
  kubecost_sa_cost_analyzer     = "kubecost-cost-analyzer"
}

# manually create here for manual service account creation
resource "kubernetes_namespace" "kubecost" {
  metadata {
    annotations = {
      name = local.kubecost_namespace
    }
    name = local.kubecost_namespace
  }
}

resource "aws_iam_policy" "kubecost_prometheus_server" {
  name        = "${var.cluster_name}-kubecost-policy-prometheus-server"
  description = "kubecost Amazon Managed Prometheus policy for prometheus-server"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "aps:RemoteWrite",
        ],

        "Resource" : [
          "arn:${local.partition}:aps:${var.region}:${local.account_id}:workspace/${aws_prometheus_workspace.kube_prometheus_stack.id}"
        ]
      }
    ]
  })
}

resource "aws_iam_role" "kubecost_prometheus_server" {
  # iam role name cannot be >64
  name = "${var.cluster_name}-kubecost-prometheus-server"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Federated : "arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
        }
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com",
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:${kubernetes_namespace.kubecost.metadata[0].name}:${local.kubecost_sa_prometheus_server}"
          }
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "kubecost_prometheus_server" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.kubecost_prometheus_server.name}"
  role       = aws_iam_role.kubecost_prometheus_server.name

  depends_on = [
    aws_iam_role.kubecost_prometheus_server,
    aws_iam_policy.kubecost_prometheus_server,
  ]
}

resource "aws_iam_policy" "kubecost_cost_analyzer" {
  name        = "${var.cluster_name}-kubecost-cost-analyzer"
  description = "kubecost cost analyzer cost-model policy"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "aps:GetLabels",
          "aps:GetMetricMetadata",
          "aps:GetSeries",
          "aps:QueryMetrics"
        ],
        "Resource" : [
          "arn:${local.partition}:aps:${var.region}:${local.account_id}:workspace/${aws_prometheus_workspace.kube_prometheus_stack.id}"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:Describe*",
          "s3:List*",
          "s3:Get*"
        ],
        "Resource" : "*"
      }
    ]
  })
}

resource "aws_iam_role" "kubecost_cost_analyzer" {
  # iam role name cannot be >64
  name = "${var.cluster_name}-kubecost-cost-analyzer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Federated : "arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
        }
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com",
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:${kubernetes_namespace.kubecost.metadata[0].name}:${local.kubecost_sa_cost_analyzer}"
          }
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "kubecost_cost_analyzer" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.kubecost_cost_analyzer.name}"
  role       = aws_iam_role.kubecost_cost_analyzer.name

  depends_on = [
    aws_iam_policy.kubecost_cost_analyzer,
    aws_iam_role.kubecost_cost_analyzer,
  ]
}

resource "kubernetes_service_account" "kubecost_cost_analyzer" {
  metadata {
    name      = local.kubecost_sa_cost_analyzer
    namespace = kubernetes_namespace.kubecost.metadata[0].name

    labels = {
      "app"                        = "cost-analyzer"
      "app.kubernetes.io/instance" = "cost-analyzer" # to be consistent with EKS add-on
      "app.kubernetes.io/name"     = "cost-analyzer"
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.kubecost_cost_analyzer.name}"
    }
  }

  # destroy an object and recreate it
  # in case of updates
  # doesn't work well with k8s objects
  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.kubecost_cost_analyzer,
  ]
}

# https://github.com/kubecost/cost-analyzer-helm-chart/blob/develop/cost-analyzer/values.yaml
#
# NOTE:
# EKS managed add-on does not support custom configuration values for prom server
# so we need to define our own
#
# ref.
# aws eks describe-addon-configuration --addon-name kubecost_kubecost --addon-version v1.103.3-eksbuild.0
# https://docs.aws.amazon.com/cli/latest/reference/eks/describe-addon-configuration.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon#example-add-on-usage-with-custom-configuration_values
# https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
# https://docs.aws.amazon.com/prometheus/latest/userguide/integrating-kubecost.html
# https://docs.kubecost.com/install-and-configure/install/provider-installations/aws-eks-cost-monitoring
resource "helm_release" "kubecost" {
  name      = local.kubecost_app_name
  namespace = kubernetes_namespace.kubecost.metadata[0].name

  # pre-create namespace in order to pre-create service account
  # in this specific namespace and to map IAM role/policy to
  # the specific service account
  create_namespace = false

  # perform pods restart during helm upgrade/rollback
  # otherwise, updates to config/values won't take effect
  recreate_pods = true
  # no need to force update
  force_update = false

  chart      = "cost-analyzer"
  repository = "https://kubecost.github.io/cost-analyzer"

  # https://github.com/kubecost/cost-analyzer-helm-chart/blob/develop/cost-analyzer/Chart.yaml
  version = "1.104.1"

  # https://prometheus.io/docs/prometheus/latest/configuration/configuration/
  # https://github.com/prometheus-community/helm-charts/blob/main/charts/kubecost/values.yaml
  values = [
    templatefile("${path.module}/helm/values/kubecost/defaults.yaml", {
      cluster_name                      = var.cluster_name
      workspace_id                      = aws_prometheus_workspace.kube_prometheus_stack.id
      remote_write_url                  = "${aws_prometheus_workspace.kube_prometheus_stack.prometheus_endpoint}api/v1/remote_write"
      remote_write_region               = var.region
      kubecost_sa_prometheus_server     = local.kubecost_sa_prometheus_server
      kubecost_sa_prometheus_server_arn = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.kubecost_prometheus_server.name}"
      kubecost_sa_cost_analyzer         = local.kubecost_sa_cost_analyzer
    }),
  ]

  depends_on = [
    kubernetes_service_account.kubecost_cost_analyzer
  ]
}

