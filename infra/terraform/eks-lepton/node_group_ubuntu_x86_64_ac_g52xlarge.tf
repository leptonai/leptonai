# "ac" means GPU accelerated.
# https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group
# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
resource "aws_eks_node_group" "ubuntu_x86_64_ac_g52xlarge" {
  # we may disable GPU node groups for CI testing
  count = var.ubuntu_x86_64_ac_g52xlarge_max_size > 0 ? 1 : 0

  cluster_name    = module.eks.cluster_name
  node_group_name = "${var.cluster_name}-ubuntu-x86_64-g52xlarge"
  node_role_arn   = aws_iam_role.mng.arn

  # no need to be in public subnets
  # when all services are exposed via ingress/LB
  subnet_ids = module.vpc.private_subnets

  scaling_config {
    min_size     = var.ubuntu_x86_64_ac_g52xlarge_min_size
    desired_size = var.ubuntu_x86_64_ac_g52xlarge_min_size
    max_size     = var.ubuntu_x86_64_ac_g52xlarge_max_size
  }
  update_config {
    max_unavailable = 1
  }

  # Force version update if existing pods are unable to be drained due to a pod disruption budget issue.
  force_update_version = false

  capacity_type  = var.default_capacity_type
  instance_types = ["g5.2xlarge"]

  # https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
  ami_type = "CUSTOM"
  launch_template {
    id      = aws_launch_template.ubuntu_x86_64_ac.id
    version = aws_launch_template.ubuntu_x86_64_ac.default_version
  }

  # not allow new pods to schedule onto the node unless they tolerate the taint
  # only the pods with matching toleration will be scheduled
  # https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group#taint-configuration-block
  taint {
    key    = "nvidia.com/gpu"
    effect = "NO_SCHEDULE"
  }

  labels = {
    # prevents unnecessary scale-outs by cluster autoscaler (see FilterOutNodesWithUnreadyResources, GPULabel)
    # the cluster autoscaler only checks the existence of the label
    # the label value can be anything, and here we label by the device name for internal use
    # https://aws.github.io/aws-eks-best-practices/cluster-autoscaling/
    # https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md#special-note-on-gpu-instances
    #
    # same as the one updated with gpu-operator
    # nvidia.com/gpu.product	NVIDIA-A10G
    "k8s.amazonaws.com/accelerator" = "NVIDIA-A10G"
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
    aws_launch_template.ubuntu_x86_64_ac,
  ]
}

resource "aws_autoscaling_group_tag" "ubuntu_x86_64_ac_g52xlarge" {
  # we may disable GPU node groups for CI testing
  count = var.ubuntu_x86_64_ac_g52xlarge_max_size > 0 ? 1 : 0

  # "*" spat expression doesn't work...
  # "resources[0].autoscaling_groups[0].name" doesn't work...
  # "*.resources[0].autoscaling_groups[0].name" doesn't work...
  # manually parse the ARN
  autoscaling_group_name = "eks-${aws_eks_node_group.ubuntu_x86_64_ac_g52xlarge[0].node_group_name}-${split("/", aws_eks_node_group.ubuntu_x86_64_ac_g52xlarge[0].arn)[length(split("/", aws_eks_node_group.ubuntu_x86_64_ac_g52xlarge[0].arn)) - 1]}"

  # add extra label in case we run cluster-autoscaler in parallel with others
  # e.g., karpenter
  tag {
    key                 = "autoscaler-kind"
    value               = "cluster-autoscaler"
    propagate_at_launch = true
  }
}
