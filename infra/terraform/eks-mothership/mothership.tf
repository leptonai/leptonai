resource "helm_release" "mothership" {
  name = "mothership"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/mothership"

  namespace = "default"

  depends_on = [
    module.vpc,
    module.eks,
    helm_release.alb_controller,
    helm_release.external_dns,
  ]
}
