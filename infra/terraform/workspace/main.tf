# https://registry.terraform.io/providers/hashicorp/time/latest/docs
resource "time_static" "activation_date" {}

provider "aws" {
  region = var.region

  # ref. https://registry.terraform.io/providers/hashicorp/aws/latest/docs#default_tags-configuration-block
  default_tags {
    tags = {
      # used for garbage collection routines
      # TEST: may be destroyed within hours of creation
      # DEV: may be destroyed within 10 days of creation (with notice)
      # PROD: destroy should never be automated
      LeptonDeploymentEnvironment = var.deployment_environment

      LeptonClusterName   = var.cluster_name
      LeptonWorkspaceName = var.workspace_name

      # created time
      # https://registry.terraform.io/providers/hashicorp/time/latest/docs
      LeptonClusterCreatedUnixSecond      = time_static.activation_date.unix
      LeptonClusterCreatedUnixTimeRFC3339 = formatdate("YYYY-MM-DD_hh-mm-ss", time_static.activation_date.rfc3339)
    }
  }
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

resource "kubernetes_resource_quota" "lepton_small_quota" {
  metadata {
    name      = "quota-${var.workspace_name}"
    namespace = var.namespace
  }

  count = var.quota_group == "small" ? 1 : 0 # Enable only when quota_group variable is "small"

  spec {
    hard = {
      "requests.cpu"            = "5"
      "requests.memory"         = "17Gi"
      "requests.nvidia.com/gpu" = 1
    }
  }

  lifecycle {
    ignore_changes = all
  }
}
