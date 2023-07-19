resource "aws_iam_policy" "alb_iam_policy" {
  name        = "${local.cluster_name}-alb-iam-policy"
  policy      = file("alb-policy.json")
  description = "ALB IAM policy"

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role" "alb_iam_role" {
  name = "${local.cluster_name}-alb-iam-role"
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
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:kube-system:aws-load-balancer-controller"
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

resource "aws_iam_role_policy_attachment" "alb_iam_role_policy_attachment" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.alb_iam_policy.name}"
  role       = aws_iam_role.alb_iam_role.name

  depends_on = [
    aws_iam_policy.alb_iam_policy,
    aws_iam_role.alb_iam_role
  ]
}

resource "kubernetes_service_account" "aws_load_balancer_controller" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"

    labels = {
      "app.kubernetes.io/component" = "controller"
      "app.kubernetes.io/name"      = "aws-load-balancer-controller"
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.alb_iam_role.name}"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.alb_iam_role_policy_attachment
  ]
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  chart      = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  namespace  = "kube-system"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "false"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  depends_on = [
    kubernetes_service_account.aws_load_balancer_controller
  ]
}
