# TEST: may be destroyed within hours of creation
# DEV: may be destroyed within 10 days of creation (with notice)
# PROD: destroy should never be automated
variable "deployment_environment" {
  description = "Deployment environment; TEST, DEV, or PROD"
  type        = string
  default     = "TEST"

  validation {
    condition     = contains(["TEST", "DEV", "PROD"], var.deployment_environment)
    error_message = "Valid 'deployment_environment' values are TEST, DEV, or PROD"
  }
}

# use "prod-admins" for PROD account
# see "infra/terraform/aws-access" for more
variable "auth_users_iam_group_name" {
  description = "AWS IAM group name whose users will be granted EKS cluster access"
  type        = string
  default     = "dev"
}

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

variable "default_capacity_type" {
  description = "Capacity type for nodes; ON_DEMAND or SPOT"
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.default_capacity_type)
    error_message = "Valid 'default_capacity_type' values are ON_DEMAND or SPOT"
  }
}

variable "lepton_cloud_route53_zone_id" {
  description = "cloud.lepton.ai Route53 zone ID"
  type        = string
  default     = "Z007822916VK7B4DFVMP7"
}

variable "single_nat_gateway" {
  description = "Determines whether to use a single-AZ NAT gateway, MUST set true for PROD"
  type        = bool
  default     = true
}

variable "disk_size_in_gb_for_node_groups" {
  description = "Default disk size for all nodes"
  type        = number
  default     = 100
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

variable "al2_x86_64_ac_g4dnxlarge_min_size" {
  description = "Min number and initial desired size of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 0
}

variable "al2_x86_64_ac_g4dnxlarge_max_size" {
  description = "Max number of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 10
}

variable "al2_x86_64_ac_g52xlarge_min_size" {
  description = "Min number and initial desired size of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 0
}

variable "al2_x86_64_ac_g52xlarge_max_size" {
  description = "Max number of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 10
}

variable "al2_x86_64_cpu_m6a16xlarge_min_size" {
  description = "Min number and initial desired size of x86_64 AL2 (Amazon Linux 2) based nodes (m6a.16xlarge)"
  type        = number
  default     = 0
}

variable "al2_x86_64_cpu_m6a16xlarge_max_size" {
  description = "Max number of x86_64 AL2 (Amazon Linux 2) based nodes (m6a.16xlarge)"
  type        = number
  default     = 10
}

variable "ubuntu_x86_64_ac_g4dnxlarge_min_size" {
  description = "Min number and initial desired size of x86_64 Ubuntu based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 0
}

variable "ubuntu_x86_64_ac_g4dnxlarge_max_size" {
  description = "Max number of x86_64 Ubuntu based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 1
}

variable "ubuntu_x86_64_ac_g52xlarge_min_size" {
  description = "Min number and initial desired size of x86_64 Ubuntu based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 0
}

variable "ubuntu_x86_64_ac_g52xlarge_max_size" {
  description = "Max number of x86_64 Ubuntu based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 1
}

variable "ubuntu_x86_64_cpu_m6a16xlarge_min_size" {
  description = "Min number and initial desired size of x86_64 Ubuntu based nodes (CPU m6a.16xlarge)"
  type        = number
  default     = 0
}

variable "ubuntu_x86_64_cpu_m6a16xlarge_max_size" {
  description = "Max number of x86_64 Ubuntu based nodes (CPU m6a.16xlarge)"
  type        = number
  default     = 10
}

variable "ubuntu_amis" {
  description = "Defines a set of custom AMIs for default managed node groups per region"
  type = map(object({
    x86_64_cpu = string
    x86_64_gpu = string
  }))

  default = {}
}
