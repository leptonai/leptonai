# https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group
# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
#
# NOTE: "var.cpu_node_group_instance_types" may be set to non-m16a instance types for testing
# but should be set to m6a instance types for production
resource "aws_eks_node_group" "ubuntu_x86_64_cpu_m6a16xlarge" {
  # NOTE: do not set "count" field here since we always want the ubuntu CPU node groups

  cluster_name    = module.eks.cluster_name
  node_group_name = "${var.cluster_name}-ubuntu-x86_64-m6a16xlarge"
  node_role_arn   = aws_iam_role.mng.arn

  # no need to be in public subnets
  # when all services are exposed via ingress/LB
  subnet_ids = module.vpc.private_subnets

  scaling_config {
    min_size     = var.ubuntu_x86_64_cpu_min_size
    desired_size = var.ubuntu_x86_64_cpu_min_size
    max_size     = var.ubuntu_x86_64_cpu_max_size
  }
  update_config {
    max_unavailable = 1
  }

  # Force version update if existing pods are unable to be drained due to a pod disruption budget issue.
  force_update_version = false

  capacity_type  = var.default_capacity_type
  instance_types = var.cpu_node_group_instance_types

  # https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
  ami_type = "CUSTOM"
  launch_template {
    id      = aws_launch_template.ubuntu_x86_64_cpu.id
    version = aws_launch_template.ubuntu_x86_64_cpu.default_version
  }

  # set same as "eks-managed-node-group" module
  lifecycle {
    create_before_destroy = true

    # Optional: Allow external changes without Terraform plan difference
    # useful when scaling up/down with cluster-autoscaler
    ignore_changes = [
      scaling_config[0].desired_size,
    ]
  }

  depends_on = [
    module.vpc,
    aws_security_group.eks,
    aws_security_group.nodes,
    aws_iam_role_policy_attachment.mng_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.mng_AmazonEC2ContainerRegistryReadOnly,
    aws_iam_role_policy_attachment.mng_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.mng_AmazonSSMFullAccess,
    aws_iam_role_policy_attachment.csi_efs_node,
    module.eks,
    aws_launch_template.ubuntu_x86_64_cpu,
  ]
}

resource "aws_autoscaling_group_tag" "ubuntu_x86_64_cpu_m6a16xlarge" {
  # NOTE: do not set "count" field here since we always want the ubuntu CPU node groups

  autoscaling_group_name = aws_eks_node_group.ubuntu_x86_64_cpu_m6a16xlarge.resources[0].autoscaling_groups[0].name

  # add extra label in case we run cluster-autoscaler in parallel with others
  # e.g., karpenter
  tag {
    key                 = "autoscaler-kind"
    value               = "cluster-autoscaler"
    propagate_at_launch = true
  }
}
