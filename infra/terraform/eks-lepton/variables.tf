variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Cluster name"
  type        = string
  default     = null
}

variable "lepton_cloud_route53_zone_id" {
  description = "cloud.lepton.ai Route53 zone ID"
  type        = string
  default     = "Z007822916VK7B4DFVMP7"
}

variable "enable_amazon_managed_prometheus" {
  description = "Determines whether to enable Amazon managed Prometheus"
  type        = bool
  default     = false
}

# this is required for Amazon Linux based AMIs
# https://github.com/leptonai/lepton/issues/225
# https://github.com/leptonai/lepton/issues/526
# https://github.com/NVIDIA/gpu-operator/issues/528
# https://catalog.ngc.nvidia.com/orgs/nvidia/teams/k8s/containers/container-toolkit/tags
# https://catalog.ngc.nvidia.com/orgs/nvidia/containers/driver/tags
# Ubuntu is preferred since amzn2 driver is broken
# errors with Failed to pull image "nvcr.io/nvidia/driver:525.105.17-amzn2"
# when ami type is "al2"
variable "use_ubuntu_nvidia_gpu_operator" {
  description = "Determines whether to NVIDIA GPU operator with ubuntu tags or centos"
  type        = bool
  default     = false
}
