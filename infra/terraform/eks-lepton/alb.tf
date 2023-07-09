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

resource "aws_iam_role_policy_attachment" "alb_iam_role_policy_attachment" {
  policy_arn = "arn:aws:iam::${local.account_id}:policy/${aws_iam_policy.alb_iam_policy.name}"
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
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${local.account_id}:role/${aws_iam_role.alb_iam_role.name}"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.alb_iam_role_policy_attachment
  ]
}

# default alb shared backend security group
# manually create rather than having ALB ingress controller create one
# because if auto-created, controller needs to block until there's an update event
# in order to trigger the security group cleanups
# which blocks the VPC deletion due to the auto-created security
# that is not tracked by this terraform state
# ref. https://github.com/kubernetes-sigs/aws-load-balancer-controller/issues/1876
# ref. https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/main/helm/aws-load-balancer-controller/values.yaml
resource "aws_security_group" "alb_shared_backend" {
  name        = "${local.cluster_name}-sg-alb-shared-backend"
  description = "[k8s] Shared Backend SecurityGroup for LoadBalancer"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    "Name" = "${local.cluster_name}-sg-alb-shared-backend"
  }

  depends_on = [
    module.vpc,
    aws_security_group.eks
  ]
}

# NOETS ON DELETION:
# DO NOT DELETE THE APPLICATION NAMESPACES WITH ALB ATTACHED
# SINCE ALB INGRESS CONTROLLER RELIES ON THE EXISTENCE OF NAMESPACE
# FOR SECURITY GROUP DELETION
# https://github.com/kubernetes-sigs/aws-load-balancer-controller/issues/1629
resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  chart      = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  namespace  = "kube-system"

  # https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/main/helm/aws-load-balancer-controller/values.yaml
  values = [yamlencode({
    clusterName  = module.eks.cluster_name
    replicaCount = "2"

    serviceAccount = {
      create = false,
      name   = "aws-load-balancer-controller"
    }

    enableBackendSecurityGroup = true
    backendSecurityGroup       = aws_security_group.alb_shared_backend.id
  })]

  depends_on = [
    kubernetes_service_account.aws_load_balancer_controller
  ]
}
