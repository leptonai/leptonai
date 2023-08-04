locals {
  metering_namespace = "metering"
  metering_app_name  = "metering"
  metering_k8s_sa    = "metering-sa"
}

resource "kubernetes_namespace" "metering" {
  metadata {
    annotations = {
      name = local.metering_namespace
    }
    name = local.metering_namespace
  }
}

resource "aws_iam_policy" "metering" {
  name        = "${var.cluster_name}-${local.metering_app_name}-policy"
  description = "metering worker IAM Policy"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "elasticfilesystem:Describe*"
        ],
        "Resource" : [
          # e.g.,
          # arn:aws:elasticfilesystem:us-east-1:605454121064:access-point/fsap-01565c1c974e3a2d3
          # arn:aws:elasticfilesystem:us-east-1:605454121064:file-system/fs-0e0b7b6b
          "arn:${local.partition}:elasticfilesystem:${var.region}:${local.account_id}:*/*"
        ],

        # TODO: limit EFS operations to this cluster only
        #
        # NOTE: "DescribeFileSystems" does not support filtering by tags
        # so we need access to all filesystems
        # otherwise, "not authorized to perform: elasticfilesystem:DescribeFileSystems on the specified resource"
        # "Condition" : {
        #   "StringEquals" : {
        #     "aws:ResourceTag/LeptonClusterName" : "${local.cluster_name}"
        #   }
        # }
      },
      {
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.IAMPolicy.html
        "Effect" : "Allow",
        "Action" : [
          "rds-db:connect"
        ],
        "Resource" : [
          "arn:${local.partition}:rds-db:${var.region}:${local.account_id}:dbuser:*/*"
        ]
      }
    ]
  })

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role" "metering" {
  name = "${var.cluster_name}-${local.metering_app_name}-role"

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

            # NOTE: do not use "kubernetes_service_account.metering.metadata[0].name"
            # it will fail due to cyclic dependency
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:${kubernetes_namespace.metering.metadata[0].name}:${local.metering_k8s_sa}"
          }
        }
      },
    ]
  })

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role_policy_attachment" "metering" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.metering.name}"
  role       = aws_iam_role.metering.name

  depends_on = [
    aws_iam_policy.metering,
    aws_iam_role.metering
  ]
}

resource "kubernetes_service_account" "metering" {
  metadata {
    name      = local.metering_k8s_sa
    namespace = kubernetes_namespace.metering.metadata[0].name

    # make sure exact match these
    # otherwise, IRSA would not work
    labels = {
      "app.kubernetes.io/instance" = local.metering_app_name
      "app.kubernetes.io/name"     = local.metering_app_name
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.metering.name}"
    }
  }

  depends_on = [
    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    kubernetes_namespace.metering,
  ]
}

# applies to all namespaces
resource "kubernetes_cluster_role" "metering" {
  metadata {
    name = "${local.metering_app_name}-cluster-role"
  }

  rule {
    api_groups = [""]
    resources  = ["events", "endpoints"]
    verbs      = ["get"]
  }

  rule {
    api_groups = [""]
    resources  = ["namespaces", "nodes", "pods", "services", "persistentvolumeclaims", "persistentvolumes"]
    verbs      = ["watch", "list", "get"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["statefulsets", "replicasets", "daemonsets"]
    verbs      = ["watch", "list", "get"]
  }

  rule {
    api_groups = ["storage.k8s.io"]
    resources  = ["storageclasses", "csinodes", "csidrivers", "csistoragecapacities"]
    verbs      = ["watch", "list", "get"]
  }

  depends_on = [
    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth
  ]
}

resource "kubernetes_cluster_role_binding" "metering" {
  metadata {
    name = "${local.metering_app_name}-cluster-role-binding"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.metering.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.metering.metadata[0].name
    namespace = kubernetes_namespace.metering.metadata[0].name
  }

  depends_on = [
    kubernetes_service_account.metering,
    kubernetes_cluster_role.metering,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth
  ]
}

# NOTE
# for RDS aurora root password, it's ok for mothership to generate here
# and store them in AWS Secrets Manager, share them across multiple
# eks-lepton clusters, since it's already protected with an IAM policy, etc.

data "aws_secretsmanager_secret" "mothership_rds_aurora_secret" {
  arn = var.mothership_rds_aurora_secret_arn
}

data "aws_secretsmanager_secret_version" "mothership_rds_aurora_secret" {
  secret_id = data.aws_secretsmanager_secret.mothership_rds_aurora_secret.id
}

resource "kubernetes_secret" "mothership_rds_aurora_secret" {
  metadata {
    name      = "mothership-rds-aurora-secret"
    namespace = kubernetes_namespace.metering.metadata[0].name
  }

  data = {
    username = jsondecode(data.aws_secretsmanager_secret_version.mothership_rds_aurora_secret.secret_string)["username"]
    password = jsondecode(data.aws_secretsmanager_secret_version.mothership_rds_aurora_secret.secret_string)["password"]
  }

  type = "Opaque"
}

# NOTE
# DO NOT pass Supabase credentials to terraform workflow
# as it may leak into terraform logging, etc.
#
# here, we assume the secrets are ALREADY stored in AWS Secrets Manager
# manually in all required regions, in all required AWS accounts,
# and just read them from there
#
# TODO: use AWS Secrets Manager "Replicate secret" feature
# if we need access from multiple regions within the same account

locals {
  supabase_credential_secret = lookup(var.supabase_credential_secret_arns, var.region, null)
}

data "aws_secretsmanager_secret" "supabase_credential_secret" {
  arn = local.supabase_credential_secret
}

data "aws_secretsmanager_secret_version" "supabase_credential_secret" {
  secret_id = data.aws_secretsmanager_secret.supabase_credential_secret.id
}

resource "kubernetes_secret" "supabase_credential_secret" {
  metadata {
    name      = "supabase-credential-secret"
    namespace = kubernetes_namespace.metering.metadata[0].name
  }

  data = {
    password = jsondecode(data.aws_secretsmanager_secret_version.supabase_credential_secret.secret_string)["password"]
  }

  type = "Opaque"
}
