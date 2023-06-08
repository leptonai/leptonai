resource "aws_iam_policy" "alb-policy" {
  name        = "alb-policy-${local.cluster_name}"
  policy      = file("alb-policy.json")
  description = "ALB IAM policy"

  depends_on = [
    module.eks,
    module.vpc
  ]
}

resource "aws_iam_role" "alb-role" {
  name = "alb-role-${local.cluster_name}"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          Federated : "arn:aws:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
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

resource "aws_iam_role_policy_attachment" "alb-role-policy-attachment" {
  policy_arn = "arn:aws:iam::${local.account_id}:policy/${aws_iam_policy.alb-policy.name}"
  role       = aws_iam_role.alb-role.name

  depends_on = [
    aws_iam_policy.alb-policy,
    aws_iam_role.alb-role
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
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${local.account_id}:role/${aws_iam_role.alb-role.name}"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.alb-role-policy-attachment
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
