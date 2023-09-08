# NOTE
# "terraform-aws-eks" implements this for you within "eks.eks_managed_node_groups" module
# but due to terraform not able to resolve "dynamic" resources
# it makes uninstall highly unstable
# we define this manually in order to install/uninstall
# in a more deterministic way without dynamic resolution
# see https://github.com/leptonai/lepton/issues/1117

# "var.create_iam_role" is default to "true"
# which is same as the previous behavior
# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/variables.tf
# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
data "aws_iam_policy_document" "mng" {
  statement {
    sid     = "EKSNodeAssumeRole"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.${data.aws_partition.current.dns_suffix}"]
    }
  }
}

# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
resource "aws_iam_role" "mng" {
  name = "${var.cluster_name}-mng-role"

  assume_role_policy = data.aws_iam_policy_document.mng.json

  # force detaching policies from this role
  # to speed up uninstall process
  force_detach_policies = true
}

locals {
  iam_role_policy_prefix = "arn:${data.aws_partition.current.partition}:iam::aws:policy"
}

# DO NOT USE "for_each" nor "dynamic"
# see https://github.com/leptonai/lepton/issues/1117
# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
resource "aws_iam_role_policy_attachment" "mng_AmazonEKSWorkerNodePolicy" {
  policy_arn = "${local.iam_role_policy_prefix}/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.mng.name
}

# DO NOT USE "for_each" nor "dynamic"
# see https://github.com/leptonai/lepton/issues/1117
# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
resource "aws_iam_role_policy_attachment" "mng_AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "${local.iam_role_policy_prefix}/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.mng.name
}

# DO NOT USE "for_each" nor "dynamic"
# see https://github.com/leptonai/lepton/issues/1117
# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
#
# "AmazonEKS_CNI_IPv6_Policy" is only required when cluster IP family is set to "ipv6"
resource "aws_iam_role_policy_attachment" "mng_AmazonEKS_CNI_Policy" {
  policy_arn = "${local.iam_role_policy_prefix}/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.mng.name
}

# used for SSM session and remote commands
# useful for debugging
resource "aws_iam_role_policy_attachment" "mng_AmazonSSMFullAccess" {
  policy_arn = "${local.iam_role_policy_prefix}/AmazonSSMFullAccess"
  role       = aws_iam_role.mng.name
}
