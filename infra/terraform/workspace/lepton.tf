resource "aws_iam_role" "api-server-role" {
  name = "api-server-role-${var.workspace_name}"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          Federated : "arn:${local.partition}:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${var.oidc_id}"
        },
        Action : "sts:AssumeRoleWithWebIdentity",
        Condition : {
          StringEquals : {
            "oidc.eks.${var.region}.amazonaws.com/id/${var.oidc_id}:aud" : "sts.amazonaws.com",
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api-server-role-s3-policy-attachment" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.s3-policy.name}"
  role       = aws_iam_role.api-server-role.name

  depends_on = [
    aws_iam_policy.s3-policy,
    aws_iam_role.api-server-role
  ]
}

resource "aws_iam_user_policy_attachment" "iam-user-s3-ro-policy-attachment" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.s3-ro-policy.name}"
  user       = aws_iam_user.s3_ro.name

  depends_on = [
    aws_iam_policy.s3-ro-policy,
    aws_iam_user.s3_ro
  ]
}

resource "aws_iam_user" "s3_ro" {
  name = "s3-ro-user-${var.workspace_name}"
}

resource "aws_iam_access_key" "s3_ro" {
  user = aws_iam_user.s3_ro.name
}

resource "kubernetes_secret" "s3_ro" {
  metadata {
    name      = "s3-ro-key"
    namespace = var.namespace
  }

  data = {
    AWS_ACCESS_KEY_ID     = aws_iam_access_key.s3_ro.id
    AWS_SECRET_ACCESS_KEY = aws_iam_access_key.s3_ro.secret
  }
}

resource "aws_iam_role_policy_attachment" "api-server-role-dynamodb-policy-attachment" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.dynamodb-policy.name}"
  role       = aws_iam_role.api-server-role.name

  depends_on = [
    aws_iam_policy.dynamodb-policy,
    aws_iam_role.api-server-role
  ]
}

locals {
  efs_exists = length(module.efs) > 0
}

resource "helm_release" "lepton" {
  name = "lepton"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/workspace"

  namespace = var.namespace

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "workspaceName"
    value = var.workspace_name
  }

  set {
    name  = "web.enabled"
    value = var.lepton_web_enabled
  }

  set {
    name  = "apiServer.serviceAccountRoleArn"
    value = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.api-server-role.name}"
  }

  set {
    name  = "apiServer.s3ReadOnlyAccessKeySecret"
    value = kubernetes_secret.s3_ro.metadata.0.name
  }

  set {
    name  = "apiServer.bucketName"
    value = aws_s3_bucket.s3-bucket.bucket
  }

  set {
    name  = "apiServer.efsID"
    value = local.efs_exists ? "${module.efs[0].id}::${module.efs[0].access_points["non_root"].id}" : ""
  }

  set {
    name  = "apiServer.certificateArn"
    value = "arn:${local.partition}:acm:${var.region}:${local.account_id}:certificate/${var.tls_cert_arn_id}"
  }

  set {
    name  = "apiServer.rootDomain"
    value = var.root_domain
  }

  set {
    name  = "apiServer.sharedAlbRootDomain"
    value = var.cluster_subdomain == "" ? "${var.cluster_name}.${var.shared_alb_root_domain}" : "${var.cluster_subdomain}.${var.shared_alb_root_domain}"
  }

  set {
    name  = "apiServer.region"
    value = var.region
  }

  set {
    name  = "apiServer.apiToken"
    value = var.api_token
  }

  set {
    name  = "apiServer.photonImageRegistry"
    value = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com"
  }

  set {
    name  = "apiServer.image.repository"
    value = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com/lepton-api-server"
  }

  set {
    name  = "apiServer.image.tag"
    value = var.image_tag_api_server
  }

  set {
    name  = "deploymentOperator.image.repository"
    value = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com/lepton-deployment-operator"
  }

  set {
    name  = "deploymentOperator.image.tag"
    value = var.image_tag_deployment_operator
  }

  set {
    name  = "web.image.repository"
    value = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com/lepton-web"
  }

  set {
    name  = "web.image.tag"
    value = var.image_tag_web
  }

  set {
    name  = "apiServer.enableTuna"
    value = var.lepton_api_server_enable_tuna
  }

  set {
    name  = "apiServer.dynamodbName"
    value = aws_dynamodb_table.tuna.name
  }

  set {
    name  = "apiServer.state"
    value = var.state
  }

  set {
    name  = "forceUpdate"
    value = timestamp()
  }

  depends_on = [
    aws_iam_role_policy_attachment.api-server-role-s3-policy-attachment,
    kubernetes_namespace.lepton,
    module.efs
  ]
}
