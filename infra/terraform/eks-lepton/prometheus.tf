# TODO: once alert manager is enabled, enable the log group
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group
# resource "aws_cloudwatch_log_group" "kube_prometheus_stack" {
#   name              = "/aws/amp/${var.cluster_name}-kube-prometheus-stack"
#   retention_in_days = 3
# }
#
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_workspace
resource "aws_prometheus_workspace" "kube_prometheus_stack" {
  alias = "${var.cluster_name}-kube-prometheus-stack"

  # TODO: once alert manager is enabled, enable the log group
  # but with more limited arn (no wildcard)
  # otherwise, "CloudWatch Logs resource policy size exceeded"
  # logging_configuration {
  #   log_group_arn = "${aws_cloudwatch_log_group.kube_prometheus_stack.arn}:*"
  # }
}

# manually create here for manual service account creation
resource "kubernetes_namespace" "kube_prometheus_stack" {
  metadata {
    annotations = {
      name = "kube-prometheus-stack"
    }
    name = "kube-prometheus-stack"
  }
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
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:kube-prometheus-stack:kube-prometheus-stack-prometheus"
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
    name      = "kube-prometheus-stack-prometheus"
    namespace = "kube-prometheus-stack"

    # this is copied from the original helm-created service account
    # ref. https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/templates/_helpers.tpl
    labels = {
      "app.kubernetes.io/component" = "prometheus"
      "app.kubernetes.io/instance"  = "kube-prometheus-stack"
      "app.kubernetes.io/name"      = "kube-prometheus-stack-prometheus"
      "app.kubernetes.io/part-of"   = "kube-prometheus-stack"
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
          "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud": "sts.amazonaws.com",
          "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub": "system:serviceaccount:kube-prometheus-stack:kube-prometheus-stack-grafana"
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
      values   = ["system:serviceaccount:kube-prometheus-stack:kube-prometheus-stack-grafana"]
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
    name      = "kube-prometheus-stack-grafana"
    namespace = "kube-prometheus-stack"

    # this is copied from the original helm-created service account
    # ref. https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/templates/_helpers.tpl
    labels = {
      "app.kubernetes.io/instance" = "kube-prometheus-stack"
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
  name      = "kube-prometheus-stack"
  namespace = "kube-prometheus-stack"

  # pre-create namespace in order to pre-create service account
  # in this specific namespace and to map IAM role/policy to
  # the specific service account
  create_namespace = false

  chart      = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"

  # https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/Chart.yaml
  # https://github.com/prometheus-community/helm-charts/releases
  version = "48.1.2"

  # https://prometheus.io/docs/prometheus/latest/configuration/configuration/
  # https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
  values = [yamlencode({
    global = {
      rbac = {
        # no need to create rbac resources
        # just let helm create them all
        # only need to overwrite service account for IRSA
        #
        # e.g.,
        # roles/kube-prometheus-stack-grafana
        # rolebindings/kube-prometheus-stack-grafana
        # clusterroles/kube-prometheus-stack-grafana-clusterrole
        # clusterroles/kube-prometheus-stack-kube-state-metrics
        # clusterroles/kube-prometheus-stack-operator
        # clusterroles/kube-prometheus-stack-prometheus
        # clusterrolebindings/kube-prometheus-stack-grafana-clusterrolebinding
        # clusterrolebindings/kube-prometheus-stack-kube-state-metrics
        # clusterrolebindings/kube-prometheus-stack-operator
        # clusterrolebindings/kube-prometheus-stack-prometheus
        create = true
      }
    }

    prometheus = {
      enabled = true

      # manually create here to set up IRSA
      #
      # e.g.,
      # serviceaccounts/kube-prometheus-stack-alertmanager
      # serviceaccounts/kube-prometheus-stack-grafana
      # serviceaccounts/kube-prometheus-stack-kube-state-metrics
      # serviceaccounts/kube-prometheus-stack-operator
      # serviceaccounts/kube-prometheus-stack-prometheus
      # serviceaccounts/kube-prometheus-stack-prometheus-node-exporter
      serviceAccount = {
        # use the one created above that maps IRSA for IAM permissions
        create = false
        name   = "kube-prometheus-stack-prometheus"
      }

      ingress = {
        # NOTE: to just use service
        #
        # e.g.,
        # <service-name>.<namespace>.svc.cluster.local:<service-port>
        # http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090
        #
        # e.g.,
        # kubectl -n kube-prometheus-stack port-forward prometheus-kube-prometheus-stack-prometheus-0 3000:9090
        # http://localhost:3000
        enabled = false
      }

      prometheusSpec = {
        scrapeInterval = "15s"
        scrapeTimeout  = "5s"
        retention      = "24h"
        retentionSize  = "100GB"
        walCompression = true

        # configure remote write
        # https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_workspace
        # https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/api.md#remotewritespec
        remoteWrite = [
          {
            name = "${var.cluster_name}-kube-prometheus-stack-remote-write-queue"
            url  = "${aws_prometheus_workspace.kube_prometheus_stack.prometheus_endpoint}api/v1/remote_write"
            sigv4 = {
              region = var.region
            }
          }
        ]

        storageSpec = {
          volumeClaimTemplate = {
            spec = {
              storageClassName = "gp3"
              resources = {
                requests = {
                  storage = "200Gi"
                }
              }
            }
          }
        }

        # https://prometheus.io/docs/prometheus/latest/configuration/configuration/#scrape_config
        # c.f., https://github.com/leptonai/lepton/pull/1369/files
        additionalScrapeConfigs = [
          # NOTE: kube-prometheus-stack already scrapes node-exporter with
          # "serviceMonitor/kube-prometheus-stack/kube-prometheus-stack-prometheus-node-exporter/0"
          # with "kubernetes_sd_configs" "role: endpoints"
          # no need to add "static_configs" "kube-prometheus-stack-prometheus-node-exporter.kube-prometheus-stack.svc.cluster.local:9100"

          {
            job_name = "lepton-deployment-pods"

            # List of Kubernetes service discovery configurations.
            # https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config
            kubernetes_sd_configs = [
              {
                role = "pod"
              }
            ]

            # https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config
            relabel_configs = [
              {
                source_labels = ["__meta_kubernetes_pod_label_photon_id"]
                action        = "keep"
                regex         = ".+"
              },
              {
                source_labels = ["__meta_kubernetes_pod_label_lepton_deployment_id"]
                action        = "keep"
                regex         = ".+"
              },
              {
                source_labels = ["__meta_kubernetes_pod_label_photon_id"]
                target_label  = "kubernetes_pod_label_photon_id"
                action        = "replace"
              },
              {
                source_labels = ["__meta_kubernetes_pod_label_lepton_deployment_id"]
                target_label  = "kubernetes_pod_label_lepton_deployment_id"
                action        = "replace"
              },
              {
                source_labels = ["__meta_kubernetes_pod_name"]
                target_label  = "kubernetes_pod_name"
                action        = "replace"
              },
              {
                source_labels = ["__meta_kubernetes_namespace"]
                target_label  = "kubernetes_namespace"
                action        = "replace"
              },
            ]
          },

          # https://github.com/NVIDIA/gpu-operator/blob/master/deployments/gpu-operator/values.yaml
          {
            job_name = "nvidia-dcgm-exporter"

            # List of labeled statically configured targets for this job.
            # https://prometheus.io/docs/prometheus/latest/configuration/configuration/#static_config
            static_configs = [
              {
                # <service-name>.<namespace>.svc.cluster.local:<service-port>
                targets = ["nvidia-dcgm-exporter.gpu-operator.svc.cluster.local:9400"]
              }
            ]
          },
        ]
      }
    }

    nodeExporter = {
      enabled = true
    }

    grafana = {
      enabled = true

      adminPassword = aws_secretsmanager_secret_version.grafana.secret_string

      # manually create here to set up IRSA
      #
      # e.g.,
      # serviceaccounts/kube-prometheus-stack-alertmanager
      # serviceaccounts/kube-prometheus-stack-grafana
      # serviceaccounts/kube-prometheus-stack-kube-state-metrics
      # serviceaccounts/kube-prometheus-stack-operator
      # serviceaccounts/kube-prometheus-stack-prometheus
      # serviceaccounts/kube-prometheus-stack-prometheus-node-exporter
      serviceAccount = {
        # use the one created above that maps IRSA for IAM permissions
        create = false
        name   = "kube-prometheus-stack-grafana"
      }

      ingress = {
        # NOTE: to just use service
        #
        # e.g.,
        # <service-name>.<namespace>.svc.cluster.local:<service-port>
        # http://kube-prometheus-stack-grafana.kube-prometheus-stack.svc.cluster.local:80
        #
        # e.g.,
        # POD=$(kubectl -n kube-prometheus-stack get pod -l app.kubernetes.io/instance=kube-prometheus-stack -l app.kubernetes.io/name=grafana -o jsonpath="{.items[0].metadata.name}")
        # kubectl -n kube-prometheus-stack port-forward $POD 3001:3000
        # http://localhost:3001
        enabled = false
      }

      sidecar = {
        datasources = {
          enabled = true

          # "Only one datasource per organization can be marked as default"
          defaultDatasourceEnabled = false
        }
      }

      # https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana
      "grafana.ini" = {
        auth = {
          sigv4_auth_enabled = true
        }

        # https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#assume_role_enabled
        aws = {
          assume_role_enabled = true
        }
      }

      # use additional data sources to configure aws auth (sig v4)
      additionalDataSources = [
        # use "http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090"
        # as fallback in case of Amazon Managed Prometheus outages
        {
          # default data source
          name      = "${var.cluster_name}-amp"
          url       = "${aws_prometheus_workspace.kube_prometheus_stack.prometheus_endpoint}"
          type      = "prometheus"
          isDefault = true
          jsonData = {
            httpMethod         = "POST"
            sigV4Auth          = true
            sigV4AuthType      = "default"
            sigV4Region        = var.region
            sigV4AssumeRoleArn = aws_iam_role.kube_prometheus_stack_grafana.arn
          }
        },
        {
          name      = "${var.cluster_name}-prometheus-server-kubecost"
          url       = "http://cost-analyzer-prometheus-server.kubecost.svc.cluster.local:80"
          type      = "prometheus"
          isDefault = false
        },
      ]
    }
  })]

  depends_on = [
    module.eks,
    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    aws_eks_addon.kubecost,
    kubernetes_service_account.kube_prometheus_stack_prometheus_server,
    kubernetes_service_account.kube_prometheus_stack_grafana,
    aws_prometheus_workspace.kube_prometheus_stack,
    null_resource.kube_prometheus_stack_grafana_update_assume_role_policy,
  ]
}
