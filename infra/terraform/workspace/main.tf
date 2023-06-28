provider "aws" {
  region = var.region
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
