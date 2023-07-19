# curl -O https://raw.githubusercontent.com/kubernetes-sigs/aws-efs-csi-driver/master/docs/iam-policy-example.json
resource "aws_iam_policy" "csi_efs" {
  name        = "${local.cluster_name}-csi-efs-policy"
  description = "CSI EFS driver IAM policy"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "elasticfilesystem:DescribeAccessPoints",
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:DescribeMountTargets",
          "ec2:DescribeAvailabilityZones"
        ],
        "Resource" : "*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "elasticfilesystem:CreateAccessPoint"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "aws:RequestTag/efs.csi.aws.com/cluster" : "true"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "elasticfilesystem:TagResource"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "aws:ResourceTag/efs.csi.aws.com/cluster" : "true"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : "elasticfilesystem:DeleteAccessPoint",
        "Resource" : "*",
        "Condition" : {
          "StringEquals" : {
            "aws:ResourceTag/efs.csi.aws.com/cluster" : "true"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientMount",
        ],
        "Resource" : "*",
        "Condition" : {
          "Bool" : {
            "elasticfilesystem:AccessedViaMountTarget" : "true"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "csi_efs" {
  name = "${local.cluster_name}-csi-efs-role"

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
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:kube-system:efs-csi-controller-sa"
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

# DO NOT USE "for_each" nor "dynamic"
# see https://github.com/leptonai/lepton/issues/1117
# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
# ref. https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html
resource "aws_iam_role_policy_attachment" "csi_efs_node" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.csi_efs.name}"
  role       = aws_iam_role.mng.name

  depends_on = [
    aws_iam_policy.csi_efs,
    aws_iam_role.mng
  ]
}

resource "aws_iam_role_policy_attachment" "csi_efs" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.csi_efs.name}"
  role       = aws_iam_role.csi_efs.name

  depends_on = [
    aws_iam_policy.csi_efs,
    aws_iam_role.csi_efs
  ]
}

resource "kubernetes_service_account" "csi_efs" {
  metadata {
    name      = "efs-csi-controller-sa"
    namespace = "kube-system"

    labels = {
      "app.kubernetes.io/name" = "aws-efs-csi-driver"
    }

    annotations = {
      "eks.amazonaws.com/role-arn" = "arn:${local.partition}:iam::${local.account_id}:role/${aws_iam_role.csi_efs.name}"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.csi_efs
  ]
}

# https://github.com/kubernetes-sigs/aws-efs-csi-driver/tree/master/charts/aws-efs-csi-driver
resource "helm_release" "csi_efs" {
  name      = "aws-efs-csi-driver"
  namespace = "kube-system"

  chart      = "aws-efs-csi-driver"
  repository = "https://kubernetes-sigs.github.io/aws-efs-csi-driver/"

  # https://github.com/kubernetes-sigs/aws-efs-csi-driver/blob/master/charts/aws-efs-csi-driver/Chart.yaml
  version = "2.4.7"

  # https://github.com/kubernetes-sigs/aws-efs-csi-driver/blob/master/charts/aws-efs-csi-driver/values.yaml
  values = [yamlencode({
    replicaCount = 2

    # https://github.com/kubernetes/autoscaler/releases
    image = {
      repository = "amazon/aws-efs-csi-driver"
      tag        = "v1.5.8"
    }

    controller = {
      create = true
      serviceAccount = {
        create = false
        name   = "efs-csi-controller-sa"
      }
    }
  })]

  depends_on = [
    module.eks,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    kubernetes_service_account.csi_efs,

    # no need to create rbac
    # https://github.com/kubernetes-sigs/aws-efs-csi-driver/blob/master/charts/aws-efs-csi-driver/templates/controller-serviceaccount.yaml
  ]
}
