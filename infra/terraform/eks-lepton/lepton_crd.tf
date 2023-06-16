resource "helm_release" "lepton_crd" {
  name = "lepton-crd"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "lepton"

  namespace = "default"

  set {
    name  = "crd.install"
    value = true
  }

  set {
    name  = "apiServer.enabled"
    value = false
  }

  set {
    name  = "deploymentOperator.enabled"
    value = false
  }

  set {
    name  = "web.enabled"
    value = false
  }

  depends_on = [
    module.eks,
    module.vpc,
    helm_release.aws_load_balancer_controller,
  ]
}
