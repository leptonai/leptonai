resource "aws_security_group" "eks" {
  name_prefix = local.cluster_name
  description = "EKS cluster security group."
  vpc_id      = module.vpc.vpc_id

  tags = {
    "Name" = "${local.cluster_name}-eks_cluster_sg"
  }
}
