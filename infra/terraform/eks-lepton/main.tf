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

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "3.19.0"

  name = "vpc-${local.cluster_name}"

  cidr = "10.0.0.0/16"
  azs  = slice(data.aws_availability_zones.available.names, 0, 3)

  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                      = 1
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"             = 1
  }
}

resource "aws_security_group" "eks" {
  name_prefix = local.cluster_name
  description = "EKS cluster security group."
  vpc_id      = module.vpc.vpc_id

  tags = {
    "Name" = "${local.cluster_name}-eks_cluster_sg"
  }
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

  eks_managed_node_groups = {
    one = {
      use_custom_launch_template = false
      name                       = "t3xlarge"

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

      instance_types = ["g4dn.xlarge"]
      disk_size      = 120

      min_size     = 0
      max_size     = 10
      desired_size = 0
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

#---------------------------------------------------------------
# GP3 Storage Class
#---------------------------------------------------------------
# This is required since intree CSI driver does not support gp3.
# Create "gp3" as default first, and later update/replace the existing "gp2".
# ref. https://github.com/leptonai/lepton/pull/532
# ref. https://aws.amazon.com/blogs/containers/amazon-ebs-csi-driver-is-now-generally-available-in-amazon-eks-add-ons/
# ref. https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/storage_class_v1
resource "kubernetes_storage_class_v1" "gp3_sc_default" {
  metadata {
    name = "gp3"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "true"
    }
  }

  storage_provisioner    = "ebs.csi.aws.com"
  reclaim_policy         = "Delete"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type      = "gp3"
    fsType    = "ext4"
    encrypted = "true"
  }
}

# make it non-default
# NOTE: "gp2" must be deleted first, before updating
# [parameters: Forbidden: updates to parameters are forbidden., provisioner: Forbidden: updates to provisioner are forbidden.]
# ref. https://github.com/hashicorp/terraform-provider-kubernetes/issues/723#issuecomment-1141833527
# ref. https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/storage_class_v1
#
# TODO
# right now we only patch, so the default encryption is "false"
# use kubernetes job to update other volume parameters
# ref. https://github.com/hashicorp/terraform-provider-kubernetes/issues/723#issuecomment-1278285213
resource "kubernetes_annotations" "gp2_sc_non_default" {
  api_version = "storage.k8s.io/v1"
  kind        = "StorageClass"
  force       = "true"

  metadata {
    name = "gp2"
  }
  annotations = {
    "storageclass.kubernetes.io/is-default-class" = "false"
  }
}

module "ebs_csi_driver_irsa" {
  source                = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version               = "~> 5.14"
  role_name             = format("%s-%s", local.cluster_name, "ebs-csi-driver")
  attach_ebs_csi_policy = true
  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}
