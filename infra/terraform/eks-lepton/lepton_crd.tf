resource "helm_release" "lepton_crd" {
  name = "lepton-crd"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/eks-lepton"

  namespace = "default"

  set {
    name  = "forceUpdate"
    value = timestamp()
  }

  set {
    name  = "sharedAlbMainDomain"
    value = var.shared_alb_main_domain
  }

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "lbGlooAlbIngress.certificateArn"
    value = aws_acm_certificate.cert.arn
  }

  set {
    name  = "lbGlooAlbIngress.namespace"
    value = local.gloo_namespace
  }

  depends_on = [
    module.eks,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    helm_release.alb_controller,

    helm_release.gloo_edge,
  ]
}
