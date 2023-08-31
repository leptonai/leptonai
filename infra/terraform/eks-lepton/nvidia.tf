# https://github.com/NVIDIA/gpu-operator/tree/master/deployments/gpu-operator
resource "helm_release" "nvidia_gpu_operator" {
  name             = "gpu-operator"
  repository       = "https://helm.ngc.nvidia.com/nvidia"
  chart            = "gpu-operator"
  namespace        = "gpu-operator"
  create_namespace = true

  # NOTE: nvidia does not use conventional version
  # https://github.com/NVIDIA/gpu-operator/blob/master/deployments/gpu-operator/Chart.yaml
  # version = "v1.0.0-devel"

  # https://github.com/NVIDIA/gpu-operator/blob/master/deployments/gpu-operator/values.yaml
  values = [
    templatefile("${path.module}/helm/values/nvidia-gpu-operator/defaults.yaml", {
      # this is required for Amazon Linux based AMIs
      # https://github.com/leptonai/lepton/issues/225
      # https://github.com/leptonai/lepton/issues/526
      # https://github.com/NVIDIA/gpu-operator/issues/528
      # https://catalog.ngc.nvidia.com/orgs/nvidia/teams/k8s/containers/container-toolkit/tags
      # Ubuntu is preferred since amzn2 driver is broken
      # errors with Failed to pull image "nvcr.io/nvidia/driver:525.105.17-amzn2"
      # when ami type is "al2"
      toolkit_version = var.use_ubuntu_nvidia_gpu_operator ? "v1.13.1-ubuntu20.04" : "v1.13.1-centos7"

      # in case "nvcr.io/nvidia/k8s" repository becomes unavailable, we copied the images to our own ECR
      # also, we DO NOT want to drop some GPU related metrics
      # so we need to include our own metrics rules for exporter
      # see https://github.com/leptonai/lepton/pull/1921 for more details
      dcgm_exporter_container_repo = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com"
    }),
  ]

  depends_on = [module.eks]
}
