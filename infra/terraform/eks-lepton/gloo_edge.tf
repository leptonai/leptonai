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

  # perf blog: https://www.solo.io/blog/envoy-at-scale-with-gloo-edge/
  # ~2000 RPS per CPU; low mem requirements
  # 1 gatewayProxy pod represents 1 envoy instance and it's the data plane of gloo
  set {
    name  = gatewayProxies.gatewayProxy.podTemplate.resources.requests.cpu
    value = "1"
  }

  set {
    name  = gatewayProxies.gatewayProxy.podTemplate.resources.requests.memory
    value = "4Gi"
  }

  set {
    name  = gatewayProxies.gatewayProxy.podTemplate.resources.limits.cpu
    value = "4"
  }

  set {
    name  = gatewayProxies.gatewayProxy.podTemplate.resources.limits.memory
    value = "16Gi"
  }

  set {
    name  = gatewayProxies.gatewayProxy.kind.deployment.replicas
    value = 3
  }

  set {
    name  = gatewayProxies.gatewayProxy.PodDisruptionBudget.minAvailable
    value = 2
  }

  # deployment/gloo is the control plane of gloo
  # It is advised not to horizontally scale the control plane components: https://docs.solo.io/gloo-edge/latest/operations/production_deployment/#horizontally-scaling-the-control-plane
  set {
    name  = gloo.deployment.resources.requests.cpu
    value = "500m"
  }

  set {
    name  = gloo.deployment.resources.requests.memory
    value = "2Gi"
  }

  set {
    name  = gloo.deployment.resources.limits.cpu
    value = "2"
  }

  set {
    name  = gloo.deployment.resources.limits.memory
    value = "8Gi"
  }

  depends_on = [module.eks]
}
