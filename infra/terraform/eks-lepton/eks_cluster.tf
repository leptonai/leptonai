locals {
  cluster_name = coalesce(var.cluster_name, "eks-${random_string.suffix.result}")
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.5.1"

  cluster_name    = local.cluster_name
  cluster_version = "1.26"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  eks_managed_node_group_defaults = {
    # required for managed node groups with "custom" AMIs to connect to EKS cluster
    # not required for default EKS-provided AMIs
    vpc_security_group_ids = [aws_security_group.nodes.id]
  }

  # https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
  eks_managed_node_groups = {
    one = {
      use_custom_launch_template = false
      name                       = "t3xlarge"
      ami_type                   = "AL2_x86_64"

      capacity_type = "ON_DEMAND" # ON_DEMAND, SPOT

      instance_types = ["t3.xlarge"]
      disk_size      = 100

      min_size     = 1
      max_size     = 10
      desired_size = 4
    }

    two = {
      use_custom_launch_template = false
      name                       = "g4dnxlarge"
      ami_type                   = "AL2_x86_64_GPU"

      capacity_type = "ON_DEMAND" # ON_DEMAND, SPOT

      instance_types = ["g4dn.xlarge"]
      disk_size      = 120

      min_size     = 0
      max_size     = 10
      desired_size = 0

      # not allow new pods to schedule onto the node unless they tolerate the taint
      # only the pods with matching toleration will be scheduled
      # https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group#taint-configuration-block
      taints = [
        {
          key    = "nvidia.com/gpu"
          effect = "NO_SCHEDULE"
        }
      ]

      # prevents unnecessary scale-outs by cluster autoscaler (see FilterOutNodesWithUnreadyResources, GPULabel)
      # the cluster autoscaler only checks the existence of the label
      # the label value can be anything, and here we label by the device name for internal use
      # https://aws.github.io/aws-eks-best-practices/cluster-autoscaling/
      # https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md#special-note-on-gpu-instances
      labels = {
        "k8s.amazonaws.com/accelerator" = "nvidia-t4"
      }
    }
  }

  create_cluster_security_group = false
  cluster_security_group_id     = aws_security_group.eks.id

  manage_aws_auth_configmap = true

  aws_auth_users = [
    for user in data.aws_iam_group.dev_members.users : {
      userarn  = "${user.arn}"
      username = "${user.user_name}"
      groups   = ["system:masters"]
    }
  ]

  depends_on = [
    module.vpc,
    aws_security_group.eks,
    aws_security_group.nodes
  ]
}

locals {
  oidc_id = substr(module.eks.cluster_oidc_issuer_url, length(module.eks.cluster_oidc_issuer_url) - 32, 32)
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    # This requires the awscli to be installed locally where Terraform is executed
    args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      # This requires the awscli to be installed locally where Terraform is executed
      args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}
