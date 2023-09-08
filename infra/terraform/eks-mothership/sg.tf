resource "aws_security_group" "eks" {
  name_prefix = "${local.cluster_name}-cluster-sg"
  description = "EKS cluster security group."
  vpc_id      = module.vpc.vpc_id

  tags = {
    "Name" = "${local.cluster_name}-cluster-sg"
  }

  depends_on = [
    module.vpc
  ]
}
