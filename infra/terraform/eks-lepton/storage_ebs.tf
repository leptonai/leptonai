# https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/4bd6454fd606d9b422702ac4c614e4039fd14156/docs/example-iam-policy.json#L4
resource "aws_iam_policy" "csi_ebs" {
  name        = "${local.cluster_name}-csi-ebs-policy"
  description = "CSI EBS driver IAM policy"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:CreateSnapshot",
          "ec2:AttachVolume",
          "ec2:DetachVolume",
          "ec2:ModifyVolume",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInstances",
          "ec2:DescribeSnapshots",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumesModifications"
        ],
        "Resource" : "*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:CreateTags"
        ],
        "Resource" : [
          "arn:${local.partition}:ec2:*:*:volume/*",
          "arn:${local.partition}:ec2:*:*:snapshot/*"
        ],
        "Condition" : {
          "StringEquals" : {
            "ec2:CreateAction" : [
              "CreateVolume",
              "CreateSnapshot"
            ]
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:DeleteTags"
        ],
        "Resource" : [
          "arn:${local.partition}:ec2:*:*:volume/*",
          "arn:${local.partition}:ec2:*:*:snapshot/*"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:CreateVolume"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "aws:RequestTag/ebs.csi.aws.com/cluster" : "true"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:CreateVolume"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "aws:RequestTag/CSIVolumeName" : "*"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:DeleteVolume"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "ec2:ResourceTag/ebs.csi.aws.com/cluster" : "true"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:DeleteVolume"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "ec2:ResourceTag/CSIVolumeName" : "*"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:DeleteVolume"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "ec2:ResourceTag/kubernetes.io/created-for/pvc/name" : "*"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:DeleteSnapshot"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "ec2:ResourceTag/CSIVolumeSnapshotName" : "*"
          }
        }
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "ec2:DeleteSnapshot"
        ],
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "ec2:ResourceTag/ebs.csi.aws.com/cluster" : "true"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "csi_ebs" {
  name = "${local.cluster_name}-csi-ebs-role"

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
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:sub" : "system:serviceaccount:kube-system:ebs-csi-controller-sa"
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

resource "aws_iam_role_policy_attachment" "csi_ebs" {
  policy_arn = "arn:${local.partition}:iam::${local.account_id}:policy/${aws_iam_policy.csi_ebs.name}"
  role       = aws_iam_role.csi_ebs.name

  depends_on = [
    aws_iam_policy.csi_ebs,
    aws_iam_role.csi_ebs
  ]
}

# https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
resource "aws_eks_addon" "csi_ebs" {
  cluster_name = module.eks.cluster_name

  # ref. "aws eks describe-addon-versions --kubernetes-version 1.26"
  addon_name    = "aws-ebs-csi-driver"
  addon_version = "v1.20.0-eksbuild.1"

  # TODO: define resolve_conflicts
  # resolve_conflicts_on_create = "OVERWRITE"
  # resolve_conflicts_on_update = "OVERWRITE"

  # whether to preserve the created resources when deleting the EKS add-on
  preserve = false

  service_account_role_arn = aws_iam_role.csi_ebs.arn

  depends_on = [
    module.eks,
    aws_iam_role_policy_attachment.csi_ebs
  ]
}
