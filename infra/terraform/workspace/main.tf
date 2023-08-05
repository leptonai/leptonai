# https://registry.terraform.io/providers/hashicorp/time/latest/docs
resource "time_static" "activation_date" {}

provider "aws" {
  region = var.region

  # ref. https://registry.terraform.io/providers/hashicorp/aws/latest/docs#default_tags-configuration-block
  default_tags {
    tags = {
      LeptonResourceKind = "workspace"

      # used for garbage collection routines
      # TEST: may be destroyed within hours of creation
      # DEV: may be destroyed within 10 days of creation (with notice)
      # PROD: destroy should never be automated
      LeptonDeploymentEnvironment = var.deployment_environment

      LeptonClusterName   = var.cluster_name
      LeptonWorkspaceName = var.workspace_name

      # created time
      # https://registry.terraform.io/providers/hashicorp/time/latest/docs
      # do not "time_static.activation_date.unix" since it may diverge between plan/apply
      # truncate the seconds here, since it's only used for resource garbage collection
      LeptonWorkspaceCreatedUnixTimeRFC3339 = var.created_unix_time_rfc3339
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # decides partition (i.e., aws, aws-gov, aws-cn)
  partition = one(data.aws_partition.current[*].partition)
}

data "aws_eks_cluster" "cluster" {
  name = var.cluster_name
}

data "aws_eks_cluster_auth" "cluster" {
  name = var.cluster_name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority.0.data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.cluster.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority.0.data)
    token                  = data.aws_eks_cluster_auth.cluster.token
  }
}

resource "kubernetes_namespace" "lepton" {
  metadata {
    name = var.namespace
    # Heavily restricted policy, following current Pod hardening best practices.
    # See https://kubernetes.io/docs/concepts/security/pod-security-standards/
    labels = {
      "pod-security.kubernetes.io/audit" = "restricted"
      # "pod-security.kubernetes.io/enforce" = "restricted"
      "pod-security.kubernetes.io/warn" = "restricted"
    }
  }
}

resource "kubernetes_resource_quota" "lepton_quota" {
  metadata {
    name      = "quota-${var.workspace_name}"
    namespace = var.namespace
  }

  count = var.enable_quota ? 1 : 0

  spec {
    hard = {
      "requests.cpu"            = tostring(var.quota_cpu)
      "requests.memory"         = "${var.quota_memory}Gi"
      "requests.nvidia.com/gpu" = var.quota_gpu
    }
  }
}
