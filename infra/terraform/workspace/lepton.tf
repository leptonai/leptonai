resource "aws_iam_role" "api-server-role" {
  name = "api-server-role-${var.cell_name}"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          Federated : "arn:aws:iam::${var.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${var.oidc_id}"
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
  policy_arn = "arn:aws:iam::${var.account_id}:policy/${aws_iam_policy.s3-policy.name}"
  role       = aws_iam_role.api-server-role.name

  depends_on = [
    aws_iam_policy.s3-policy,
    aws_iam_role.api-server-role
  ]
}

resource "aws_iam_role_policy_attachment" "api-server-role-dynamodb-policy-attachment" {
  policy_arn = "arn:aws:iam::${var.account_id}:policy/${aws_iam_policy.dynamodb-policy.name}"
  role       = aws_iam_role.api-server-role.name

  depends_on = [
    aws_iam_policy.dynamodb-policy,
    aws_iam_role.api-server-role
  ]
}

resource "helm_release" "lepton" {
  name = "lepton"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/lepton"

  namespace = var.namespace

  set {
    name  = "clusterName"
    value = var.cell_name
  }

  set {
    name  = "web.enabled"
    value = var.lepton_web_enabled
  }

  set {
    name  = "crd.install"
    value = false
  }

  set {
    name  = "apiServer.serviceAccountRoleArn"
    value = "arn:aws:iam::${var.account_id}:role/${aws_iam_role.api-server-role.name}"
  }

  set {
    name  = "apiServer.bucketName"
    value = aws_s3_bucket.s3-bucket.bucket
  }

  set {
    name  = "apiServer.certificateArn"
    value = "arn:aws:acm:${var.region}:${var.account_id}:certificate/${var.tls_cert_arn_id}"
  }

  set {
    name  = "apiServer.rootDomain"
    value = var.root_domain
  }

  set {
    name  = "apiServer.cellName"
    value = var.cell_name
  }

  set {
    name  = "apiServer.apiToken"
    value = var.api_token
  }

  set {
    name  = "apiServer.image.tag"
    value = var.image_tag_api_server
  }

  set {
    name  = "deploymentOperator.image.tag"
    value = var.image_tag_deployment_operator
  }

  set {
    name  = "web.image.tag"
    value = var.image_tag_web
  }

  set {
    name  = "apiServer.enableTuna"
    value = var.lepton_api_server_enable_tuna
  }

  depends_on = [
    aws_iam_role_policy_attachment.api-server-role-s3-policy-attachment,
    kubernetes_namespace.lepton
  ]
}
