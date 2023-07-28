resource "helm_release" "gloo_edge" {
  name       = "gloo-edge"
  repository = "https://storage.googleapis.com/solo-public-helm"
  chart      = "gloo"
  namespace  = "gloo-system"

  # https://github.com/solo-io/gloo/blob/main/install/helm/gloo/Chart-template.yaml
  # https://github.com/solo-io/gloo/blob/main/install/helm/gloo/values-template.yaml
  # https://docs.solo.io/gloo-edge/latest/reference/helm_chart_values/open_source_helm_chart_values/
  # https://github.com/solo-io/gloo/releases
  version = "v1.13.23"

  create_namespace = true

  depends_on = [module.eks]
}
