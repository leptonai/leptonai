resource "aws_iam_role" "mothership_role" {
  name = "mothership-role"

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
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

locals {
  iam_role_policy_prefix = "arn:${data.aws_partition.current.partition}:iam::aws:policy"
}

resource "aws_iam_role_policy_attachment" "mothership_role" {
  policy_arn = "${local.iam_role_policy_prefix}/AdministratorAccess"
  role       = aws_iam_role.mothership_role.name
  depends_on = [aws_iam_role.mothership_role]
}

resource "helm_release" "mothership" {
  name = "mothership"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/mothership"

  namespace = "default"

  set {
    name  = "mothership.image.repository"
    value = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com/lepton-mothership"
  }

  # TODO: create the role using terraform
  set {
    name  = "mothership.serviceAccountRoleArn"
    value = aws_iam_role.mothership_role.arn
  }

  set {
    name  = "mothership.apiToken"
    value = var.api_token
  }

  set {
    name  = "mothership.certificateArn"
    value = "arn:${local.partition}:acm:${var.region}:${local.account_id}:certificate/${var.tls_cert_arn_id}"
  }

  set {
    name  = "mothership.rootDomain"
    value = var.root_hostname
  }

  set {
    name  = "mothership.deploymentEnvironment"
    value = var.deployment_environment
  }

  depends_on = [
    module.vpc,
    module.eks,
    helm_release.alb_controller,
    helm_release.external_dns,
    aws_iam_role_policy_attachment.mothership_role,
  ]
}