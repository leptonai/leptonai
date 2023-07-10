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

  create_cluster_security_group = false
  cluster_security_group_id     = aws_security_group.eks.id

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

locals {
  aws_auth_users = [
    for user in data.aws_iam_group.dev_members.users : {
      userarn  = "${user.arn}"
      username = "${user.user_name}"
      groups   = ["system:masters"]
    }
  ]
  aws_auth_configmap_data = {
    mapUsers = yamlencode(local.aws_auth_users)
  }
}

# NEED SEPARATE resource
# "eks" module with "manage_aws_auth_configmap=true"
# does not work if we separate out the node groups
# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/tree/master/modules/eks-managed-node-group
resource "kubernetes_config_map" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = local.aws_auth_configmap_data

  lifecycle {
    # We are ignoring the data here since we will manage it with the resource below
    # This is only intended to be used in scenarios where the configmap does not exist
    ignore_changes = [data, metadata[0].labels, metadata[0].annotations]
  }
}

# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/tree/master/modules/eks-managed-node-group
resource "kubernetes_config_map_v1_data" "aws_auth" {
  force = true

  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = local.aws_auth_configmap_data

  depends_on = [
    module.eks,
    kubernetes_config_map.aws_auth
  ]
}
