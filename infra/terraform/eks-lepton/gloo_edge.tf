resource "helm_release" "gloo_edge" {
  name       = "gloo-edge"
  repository = "https://storage.googleapis.com/solo-public-helm"
  chart      = "gloo"
  namespace  = local.gloo_namespace

  # https://github.com/solo-io/gloo/blob/main/install/helm/gloo/Chart-template.yaml
  # https://github.com/solo-io/gloo/blob/main/install/helm/gloo/values-template.yaml
  # https://docs.solo.io/gloo-edge/latest/reference/helm_chart_values/open_source_helm_chart_values/
  # https://github.com/solo-io/gloo/releases
  version = "v1.13.23"

  create_namespace = true

  # https://docs.solo.io/gloo-edge/latest/operations/production_deployment/#performance-tips
  # disable unnecessary options to improve performance; we always create upstreams explicitly, 
  # and we don't use kube service **directly** as destination, therefore these are not necessary.
  set {
    name  = "discovery.udsOptions.enabled"
    value = false
  }

  depends_on = [module.eks]
}
