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

  depends_on = [
    module.eks,

    # k8s object requires access to EKS cluster via aws-auth
    # also required for deletion
    # this ensures deleting this object happens before aws-auth
    kubernetes_config_map_v1_data.aws_auth,

    helm_release.alb_controller,
  ]
}
