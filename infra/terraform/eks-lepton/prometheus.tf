locals {
  kube_prometheus_stack_namespace            = "kube-prometheus-stack"
  kube_prometheus_stack_app_name             = "kube-prometheus-stack"
  kube_prometheus_stack_sa_prometheus_server = "kube-prometheus-stack-prometheus"
  kube_prometheus_stack_sa_grafana           = "kube-prometheus-stack-grafana"
}

# manually create here for manual service account creation
resource "kubernetes_namespace" "kube_prometheus_stack" {
  metadata {
    annotations = {
      name = local.kube_prometheus_stack_namespace
    }
    name = local.kube_prometheus_stack_namespace
  }
}

# TODO: once alert manager is enabled, enable the log group
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group
# resource "aws_cloudwatch_log_group" "kube_prometheus_stack" {
#   name              = "/aws/amp/${var.cluster_name}-kube-prometheus-stack"
#   retention_in_days = 3
# }
#
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_workspace
resource "aws_prometheus_workspace" "kube_prometheus_stack" {
  alias = "${var.cluster_name}-${local.kube_prometheus_stack_app_name}"

  # TODO: once alert manager is enabled, enable the log group
  # but with more limited arn (no wildcard)
  # otherwise, "CloudWatch Logs resource policy size exceeded"
  # logging_configuration {
  #   log_group_arn = "${aws_cloudwatch_log_group.kube_prometheus_stack.arn}:*"
  # }
}

# policy for prometheus-server with write-only access
#
# do not use managed policy "AmazonPrometheusRemoteWriteAccess"
# since we want to limit access to a specific amp workspace
# ref. https://docs.aws.amazon.com/prometheus/latest/userguide/security_iam_id-based-policy-examples.html#security_iam_amp_policies
#
# this policy is only for prometheus-server
# prometheus-server needs write access
resource "aws_iam_policy" "kube_prometheus_stack_prometheus_server" {
  name        = "${var.cluster_name}-kube-prometheus-stack-policy-prometheus-server"
  description = "kube-prometheus-stack Amazon Managed Prometheus policy for prometheus-server"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "aps:RemoteWrite",
        ],

        # amp does not support arn based on alias, also wildcard does not work
        # specify the exact workspace id we need to grant
        # e.g.,
        # not authorized to perform: aps:RemoteWrite on resource: arn:${local.partition}:aps:us-east-1:605454121064:workspace/ws-99847e3b...
        "Resource" : [
          "arn:${local.partition}:aps:${var.region}:${local.account_id}:workspace/${aws_prometheus_workspace.kube_prometheus_stack.id}"
        ]
      }
    ]
  })

  depends_on = [
    module.eks,
    aws_prometheus_workspace.kube_prometheus_stack,
    aws_iam_role.kube_prometheus_stack_prometheus_server,
  ]
}

# role for prometheus-server
resource "aws_iam_role" "kube_prometheus_stack_prometheus_server" {
  # iam role name cannot be >64
  name = "${var.cluster_name}-prom-server"

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
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:${kubernetes_namespace.kube_prometheus_stack.metadata[0].name}:${local.kube_prometheus_stack_sa_prometheus_server}"
          }
        }
      },
    ]
  })

  depends_on = [
    module.eks,
    module.vpc,
  ]
}

resource "aws_iam_role_policy_attachment" "kube_prometheus_stack_prometheus_server" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.kube_prometheus_stack_prometheus_server.name}"
  role       = aws_iam_role.kube_prometheus_stack_prometheus_server.name

  depends_on = [
    aws_iam_role.kube_prometheus_stack_prometheus_server,
    aws_iam_policy.kube_prometheus_stack_prometheus_server,
  ]
}

# "helm_release.kube_prometheus_stack" creates default service accounts
# but without amazon managed prometheus remote write enabled service accounts
# overwrite here
resource "kubernetes_service_account" "kube_prometheus_stack_prometheus_server" {
  metadata {
    name      = local.kube_prometheus_stack_sa_prometheus_server
    namespace = kubernetes_namespace.kube_prometheus_stack.metadata[0].name

    # this is copied from the original helm-created service account
    # ref. https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/templates/_helpers.tpl
    labels = {
      "app.kubernetes.io/component" = "prometheus"
      "app.kubernetes.io/instance"  = local.kube_prometheus_stack_app_name
      "app.kubernetes.io/name"      = "kube-prometheus-stack-prometheus"
      "app.kubernetes.io/part-of"   = local.kube_prometheus_stack_app_name
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.kube_prometheus_stack_prometheus_server.name}"
    }
  }

  # destroy an object and recreate it
  # in case of updates
  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    kubernetes_namespace.kube_prometheus_stack,
    aws_iam_role_policy_attachment.kube_prometheus_stack_prometheus_server,
  ]
}

# role for grafana
# ref. "AmazonGrafanaServiceRole"
resource "aws_iam_role" "kube_prometheus_stack_grafana" {
  # iam role name cannot be >64
  name = "${var.cluster_name}-grafana"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Principal": {
        "Federated": "arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
      },
      "Condition" : {
        "StringEquals": {
          "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com",
          "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:${kubernetes_namespace.kube_prometheus_stack.metadata[0].name}:${local.kube_prometheus_stack_sa_grafana}"
        }
      }
    }
  ]
}
EOF

  # prevent role to get reverted in the next subsequent terraform run
  lifecycle {
    ignore_changes = [
      # basically, ignore changes made after creation
      # and let "local-exec" update the inline policy
      # for trusting the role itself (required for grafana access)
      assume_role_policy,
    ]
  }

  depends_on = [
    module.eks,
    module.vpc,
  ]
}

# policy for grafana with read-only access
#
# do not use managed policy "AmazonPrometheusQueryAccess"
# since we want to limit access to a specific amp workspace
# ref. https://docs.aws.amazon.com/prometheus/latest/userguide/security_iam_id-based-policy-examples.html#security_iam_amp_policies
#
# this policy is shared between prometheus-server and grafana
# prometheus-server needs write access
# grafana only needs read access
resource "aws_iam_policy" "kube_prometheus_stack_grafana" {
  name        = "${var.cluster_name}-grafana"
  description = "kube-prometheus-stack Amazon Managed Prometheus policy for grafana"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "aps:GetLabels",
          "aps:GetMetricMetadata",
          "aps:GetSeries",
          "aps:QueryMetrics",
        ],

        # amp does not support arn based on alias, also wildcard does not work
        # specify the exact workspace id we need to grant
        # e.g.,
        # not authorized to perform: aps:RemoteWrite on resource: arn:${local.partition}:aps:us-east-1:605454121064:workspace/ws-99847e3b...
        "Resource" : [
          "arn:${local.partition}:aps:${var.region}:${local.account_id}:workspace/${aws_prometheus_workspace.kube_prometheus_stack.id}"
        ]
      }
    ]
  })

  depends_on = [
    module.eks,
    aws_prometheus_workspace.kube_prometheus_stack,
    aws_iam_role.kube_prometheus_stack_grafana,
  ]
}

resource "aws_iam_role_policy_attachment" "kube_prometheus_stack_grafana" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.kube_prometheus_stack_grafana.name}"
  role       = aws_iam_role.kube_prometheus_stack_grafana.name

  depends_on = [
    aws_iam_policy.kube_prometheus_stack_grafana,
    aws_iam_role.kube_prometheus_stack_grafana,
  ]
}

# assume role itself is required for grafana dashboard to access amp
# without "sts:AssumeRole", error:
# not authorized to perform: sts:AssumeRole on resource: arn:${local.partition}:iam::...
# "jsonencode" does not work...
# MalformedPolicyDocument: Invalid principal in policy: "AWS"
#
# go-sdk/terraform does not support assume role itself unless already created
# ref. https://github.com/hashicorp/terraform-provider-aws/issues/8905
# ref. https://github.com/hashicorp/terraform-provider-aws/issues/27034
# ref. https://aws.amazon.com/blogs/security/announcing-an-update-to-iam-role-trust-policy-behavior/
# ref. https://www.reddit.com/r/Terraform/comments/10g4z6s/create_selfassuming_selftrusting_iam_role/
data "aws_iam_policy_document" "kube_prometheus_stack_grafana_update_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"]
    }
    condition {
      test     = "StringEquals"
      values   = ["sts.amazonaws.com"]
      variable = "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud"
    }
    condition {
      test     = "StringEquals"
      values   = ["system:serviceaccount:${kubernetes_namespace.kube_prometheus_stack.metadata[0].name}:${local.kube_prometheus_stack_sa_grafana}"]
      variable = "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub"
    }
  }

  statement {
    sid     = ""
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:${local.partition}:iam::${local.account_id}:role/${var.cluster_name}-grafana"]
    }
  }
}

resource "null_resource" "kube_prometheus_stack_grafana_update_assume_role_policy" {
  provisioner "local-exec" {
    # sleep first since IAM propagation may take awhile
    # otherwise, the update command will fail
    command = "sleep 10; aws iam update-assume-role-policy --role-name ${aws_iam_role.kube_prometheus_stack_grafana.name} --policy-document '${data.aws_iam_policy_document.kube_prometheus_stack_grafana_update_assume_role_policy.json}'"
  }

  triggers = {
    trigger = sha256(data.aws_iam_policy_document.kube_prometheus_stack_grafana_update_assume_role_policy.json)
    "after" = aws_iam_role.kube_prometheus_stack_grafana.assume_role_policy
  }

  depends_on = [
    aws_iam_role.kube_prometheus_stack_grafana,
    data.aws_iam_policy_document.kube_prometheus_stack_grafana_update_assume_role_policy
  ]
}

# "helm_release.kube_prometheus_stack" creates default service accounts
# but without amazon managed prometheus remote write enabled service accounts
# overwrite here
resource "kubernetes_service_account" "kube_prometheus_stack_grafana" {
  metadata {
    name      = local.kube_prometheus_stack_sa_grafana
    namespace = kubernetes_namespace.kube_prometheus_stack.metadata[0].name

    # this is copied from the original helm-created service account
    # ref. https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/templates/_helpers.tpl
    labels = {
      "app.kubernetes.io/instance" = local.kube_prometheus_stack_app_name
      "app.kubernetes.io/name"     = "grafana"
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.kube_prometheus_stack_grafana.name}"
    }
  }

  # destroy an object and recreate it
  # in case of updates
  # doesn't work well with k8s objects
  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    kubernetes_namespace.kube_prometheus_stack,
    aws_iam_role_policy_attachment.kube_prometheus_stack_grafana,
  ]
}

# https://github.com/awslabs/data-on-eks/tree/main
resource "random_password" "grafana" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# https://github.com/awslabs/data-on-eks/tree/main
#tfsec:ignore:aws-ssm-secret-use-customer-key
resource "aws_secretsmanager_secret" "grafana" {
  name                    = "${var.cluster_name}-grafana-${random_string.suffix.result}"
  recovery_window_in_days = 0 # Set to zero for this example to force delete during Terraform destroy
}

# https://github.com/awslabs/data-on-eks/tree/main
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version
resource "aws_secretsmanager_secret_version" "grafana" {
  secret_id     = aws_secretsmanager_secret.grafana.id
  secret_string = random_password.grafana.result
}

# https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
# https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
resource "helm_release" "kube_prometheus_stack" {
  name      = local.kube_prometheus_stack_app_name
  namespace = kubernetes_namespace.kube_prometheus_stack.metadata[0].name

  # pre-create namespace in order to pre-create service account
  # in this specific namespace and to map IAM role/policy to
  # the specific service account
  create_namespace = false

  # perform pods restart during helm upgrade/rollback
  # otherwise, updates to config/values won't take effect
  recreate_pods = true
  # no need to force update
  force_update = false

  chart      = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"

  # https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/Chart.yaml
  # https://github.com/prometheus-community/helm-charts/releases
  version = "48.1.2"

  # https://prometheus.io/docs/prometheus/latest/configuration/configuration/
  # https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
  values = [
    templatefile("${path.module}/helm/values/kube-prometheus-stack/defaults.yaml", {
    }),

    length(var.alertmanager_slack_webhook_url) > 0 ? templatefile("${path.module}/helm/values/kube-prometheus-stack/alertmanager.yaml", {
      alertmanager_priorityclass     = ""
      alertmanager_slack_channel     = var.alertmanager_slack_channel
      alertmanager_slack_webhook_url = var.alertmanager_slack_webhook_url
      alertmanager_target_namespaces = var.alertmanager_target_namespaces
      alertmanager_eks               = var.local.cluster_name
    }) : file("${path.module}/helm/values/kube-prometheus-stack/alertmanager-disabled.yaml"),

    templatefile("${path.module}/helm/values/kube-prometheus-stack/prometheus-server.yaml", {
      kube_prometheus_stack_sa_prometheus_server = local.kube_prometheus_stack_sa_prometheus_server
      remote_write_name                          = "${var.cluster_name}-kube-prometheus-stack-remote-write-queue"
      remote_write_url                           = "${aws_prometheus_workspace.kube_prometheus_stack.prometheus_endpoint}api/v1/remote_write"
      remote_write_region                        = var.region
    }),
    templatefile("${path.module}/helm/values/kube-prometheus-stack/prometheus-server-rules.yaml", {
      alertmanager_target_namespaces = var.alertmanager_target_namespaces
    }),

    templatefile("${path.module}/helm/values/kube-prometheus-stack/kubelet.yaml", {
    }),

    templatefile("${path.module}/helm/values/kube-prometheus-stack/node_exporter.yaml", {
    }),

    templatefile("${path.module}/helm/values/kube-prometheus-stack/kube-state-metrics.yaml", {
    }),

    templatefile("${path.module}/helm/values/kube-prometheus-stack/grafana.yaml", {
      admin_password                   = aws_secretsmanager_secret_version.grafana.secret_string
      kube_prometheus_stack_sa_grafana = local.kube_prometheus_stack_sa_grafana
      amp_name                         = "${var.cluster_name}-amp"
      amp_url                          = "${aws_prometheus_workspace.kube_prometheus_stack.prometheus_endpoint}"
      amp_region                       = var.region
      amp_role_arn                     = aws_iam_role.kube_prometheus_stack_grafana.arn
      kubecost_name                    = "${var.cluster_name}-prometheus-server-kubecost"
      kubecost_url                     = "http://cost-analyzer-prometheus-server.kubecost.svc.cluster.local:80"
    }),
  ]

  depends_on = [
    module.eks,
    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    kubernetes_service_account.kube_prometheus_stack_prometheus_server,
    kubernetes_service_account.kube_prometheus_stack_grafana,
    aws_prometheus_workspace.kube_prometheus_stack,
    null_resource.kube_prometheus_stack_grafana_update_assume_role_policy,
  ]
}
