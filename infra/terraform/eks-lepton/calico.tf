resource "helm_release" "calico" {
  name             = "calico"
  repository       = "https://docs.tigera.io/calico/charts"
  chart            = "tigera-operator"
  namespace        = "tigera-operator"
  version          = "v3.26.1"
  create_namespace = true

  depends_on = [module.eks]
}
