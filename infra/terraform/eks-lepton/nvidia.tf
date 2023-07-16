# https://github.com/NVIDIA/gpu-operator/tree/master/deployments/gpu-operator
resource "helm_release" "nvidia_gpu_operator" {
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
      # Ubuntu is preferred since amzn2 driver is broken
      # errors with Failed to pull image "nvcr.io/nvidia/driver:525.105.17-amzn2"
      # when ami type is "al2"
      version = var.use_ubuntu_nvidia_gpu_operator ? "v1.13.1-ubuntu20.04" : "v1.13.1-centos7"
    }
  })]

  depends_on = [module.eks]
}
