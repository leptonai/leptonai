# "ac" means GPU accelerated.
# https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group
# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
resource "aws_eks_node_group" "al2_x86_64_ac_g52xlarge" {
  # TODO
  # can't really disable with "count" since tf will error
  # "attributes must be accessed on specific instances."
  # just remove once ubuntu GPU nodes are stable

  cluster_name    = module.eks.cluster_name
  node_group_name = "${var.cluster_name}-al2-x86_64-g52xlarge"
  node_role_arn   = aws_iam_role.mng.arn

  # no need to be in public subnets
  # when all services are exposed via ingress/LB
  subnet_ids = module.vpc.private_subnets

  # can only specify kubernetes version without an image id
  version = "1.26"

  scaling_config {
    min_size     = var.al2_x86_64_ac_g52xlarge_min_size
    desired_size = var.al2_x86_64_ac_g52xlarge_min_size
    max_size     = var.al2_x86_64_ac_g52xlarge_max_size
  }
  update_config {
    max_unavailable = 1
  }

  # Force version update if existing pods are unable to be drained due to a pod disruption budget issue.
  force_update_version = false

  capacity_type  = var.default_capacity_type
  instance_types = ["g5.2xlarge"]

  # NOTE: EKS uses non-NVME based AMIs for root volume
  # so the instance store for g5 instance will be ignored
  # instead using EBS for root volume
  # ref. https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/add-instance-store-volumes.html
  disk_size = var.disk_size_in_gb_for_node_groups

  # https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
  ami_type = "AL2_x86_64_GPU"

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
    "k8s.amazonaws.com/accelerator" = "nvidia-a10g"
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

  # NOTE: no need for "launch_template"
  # EKS managed node group provides one for AL2 nodes

  depends_on = [
    module.vpc,
    aws_security_group.eks,
    aws_security_group.nodes,
    aws_iam_role_policy_attachment.mng_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.mng_AmazonEC2ContainerRegistryReadOnly,
    aws_iam_role_policy_attachment.mng_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.csi_efs_node,
    module.eks
  ]
}

# TODO
# can't really disable with "count" since tf will error
# "attributes must be accessed on specific instances."
# just remove once ubuntu GPU nodes are stable
resource "aws_autoscaling_group_tag" "al2_x86_64_ac_g52xlarge" {
  autoscaling_group_name = aws_eks_node_group.al2_x86_64_ac_g52xlarge.resources[0].autoscaling_groups[0].name

  # add extra label in case we run cluster-autoscaler in parallel with others
  # e.g., karpenter
  tag {
    key                 = "autoscaler-kind"
    value               = "cluster-autoscaler"
    propagate_at_launch = true
  }
}