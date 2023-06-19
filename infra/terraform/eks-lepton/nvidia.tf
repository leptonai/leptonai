resource "helm_release" "gpu-operator" {
  name             = "gpu-operator"
  repository       = "https://helm.ngc.nvidia.com/nvidia"
  chart            = "gpu-operator"
  namespace        = "gpu-operator"
  create_namespace = true

  # https://github.com/NVIDIA/gpu-operator/blob/master/deployments/gpu-operator/values.yaml
  values = [yamlencode({
    toolkit = {
      # this is required for Amazon Linux based AMIs
      # https://github.com/leptonai/lepton/issues/225
      # https://github.com/leptonai/lepton/issues/526
      # https://github.com/NVIDIA/gpu-operator/issues/528
      # https://catalog.ngc.nvidia.com/orgs/nvidia/teams/k8s/containers/container-toolkit/tags
      version = "v1.13.1-centos7"
    }
  })]

  depends_on = [module.eks]
}
