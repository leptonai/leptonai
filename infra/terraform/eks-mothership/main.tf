provider "aws" {
  region = var.region
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

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_iam_group" "dev_members" {
  group_name = "dev"
}

locals {
  cluster_name = coalesce(var.cluster_name, "eks-${random_string.suffix.result}")
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
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
    ami_type = "AL2_x86_64"
  }

  # https://docs.aws.amazon.com/eks/latest/APIReference/API_Nodegroup.html
  eks_managed_node_groups = {
    one = {
      use_custom_launch_template = false
      name                       = "t3xlarge"

      instance_types = ["t3.xlarge"]
      disk_size      = 100

      min_size     = 1
      max_size     = 2
      desired_size = 2
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
}

locals {
  oidc_id    = substr(module.eks.cluster_oidc_issuer_url, length(module.eks.cluster_oidc_issuer_url) - 32, 32)
  account_id = data.aws_caller_identity.current.account_id
}
