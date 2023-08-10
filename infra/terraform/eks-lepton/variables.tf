# overwrites "LeptonClusterCreatedUnixTimeRFC3339" for AWS resource tagging
variable "created_unix_time_rfc3339" {
  description = "Cluster created unix time in RFC3339 format with hour precision"
  type        = string
  default     = "2023-08-05T00"
}

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

variable "shared_alb_root_domain" {
  description = "Root domain for workspaces on a ALB shared aross the cluster"
  type        = string
  default     = "dev.lepton.ai"
}

variable "cluster_subdomain" {
  description = "Subdomain alias for the cluster, e.g. `prod` in domain `prod.app.lepton.ai`"
  type        = string
  default     = ""
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

variable "cpu_node_group_instance_types" {
  description = "List of EC2 instance types to use/overwrite for CPU node groups (useful for testing with lower spot availability)"
  type        = list(string)
  default     = ["m6a.16xlarge"]
}

variable "lepton_cloud_route53_zone_id" {
  description = "cloud.lepton.ai Route53 zone ID"
  type        = string
  default     = "Z007822916VK7B4DFVMP7"
}

variable "single_nat_gateway" {
  description = "Determines whether to use a single-AZ NAT gateway, MUST set true for PROD (set true for TEST/DEV to save costs)"
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

  validation {
    condition     = var.al2_x86_64_ac_g4dnxlarge_min_size >= 0
    error_message = "MUST: al2_x86_64_ac_g4dnxlarge_min_size >=0"
  }
}

variable "al2_x86_64_ac_g4dnxlarge_max_size" {
  description = "Max number of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 10

  validation {
    # all AL2 nodes are optional, only required for fallback, thus ok to set it to 0
    condition     = var.al2_x86_64_ac_g4dnxlarge_max_size >= 0
    error_message = "MUST: al2_x86_64_ac_g4dnxlarge_max_size >=0"
  }
}

variable "al2_x86_64_ac_g52xlarge_min_size" {
  description = "Min number and initial desired size of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 0

  validation {
    condition     = var.al2_x86_64_ac_g52xlarge_min_size >= 0
    error_message = "MUST: al2_x86_64_ac_g52xlarge_min_size >=0"
  }
}

variable "al2_x86_64_ac_g52xlarge_max_size" {
  description = "Max number of x86_64 AL2 (Amazon Linux 2) based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 10

  validation {
    # all AL2 nodes are optional, only required for fallback, thus ok to set it to 0
    condition     = var.al2_x86_64_ac_g52xlarge_max_size >= 0
    error_message = "MUST: al2_x86_64_ac_g52xlarge_max_size >=0"
  }
}

variable "al2_x86_64_cpu_min_size" {
  description = "Min number and initial desired size of x86_64 AL2 (Amazon Linux 2) based nodes (m6a.16xlarge)"
  type        = number
  default     = 0

  validation {
    condition     = var.al2_x86_64_cpu_min_size >= 0
    error_message = "MUST: al2_x86_64_cpu_min_size >=0"
  }
}

variable "al2_x86_64_cpu_max_size" {
  description = "Max number of x86_64 AL2 (Amazon Linux 2) based nodes (m6a.16xlarge)"
  type        = number
  default     = 10

  validation {
    # all AL2 nodes are optional, only required for fallback, thus ok to set it to 0
    condition     = var.al2_x86_64_cpu_max_size >= 0
    error_message = "MUST: al2_x86_64_cpu_max_size >=0"
  }
}

variable "ubuntu_x86_64_ac_g4dnxlarge_min_size" {
  description = "Min number and initial desired size of x86_64 Ubuntu based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 0

  validation {
    condition     = var.ubuntu_x86_64_ac_g4dnxlarge_min_size >= 0
    error_message = "MUST: ubuntu_x86_64_ac_g4dnxlarge_min_size >=0"
  }
}

variable "ubuntu_x86_64_ac_g4dnxlarge_max_size" {
  description = "Max number of x86_64 Ubuntu based nodes (GPU with NVIDIA T4 device)"
  type        = number
  default     = 1

  validation {
    # optionally, don't create GPU nodes, so ok to set this to zero
    condition     = var.ubuntu_x86_64_ac_g4dnxlarge_max_size >= 0
    error_message = "MUST: ubuntu_x86_64_ac_g4dnxlarge_max_size >=0"
  }
}

variable "ubuntu_x86_64_ac_g52xlarge_min_size" {
  description = "Min number and initial desired size of x86_64 Ubuntu based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 0

  validation {
    condition     = var.ubuntu_x86_64_ac_g52xlarge_min_size >= 0
    error_message = "MUST: ubuntu_x86_64_ac_g52xlarge_min_size >=0"
  }
}

variable "ubuntu_x86_64_ac_g52xlarge_max_size" {
  description = "Max number of x86_64 Ubuntu based nodes (GPU with NVIDIA A10G device)"
  type        = number
  default     = 1

  validation {
    # optionally, don't create GPU nodes, so ok to set this to zero
    condition     = var.ubuntu_x86_64_ac_g52xlarge_max_size >= 0
    error_message = "MUST: ubuntu_x86_64_ac_g52xlarge_max_size >=0"
  }
}

variable "ubuntu_x86_64_cpu_min_size" {
  description = "Min number and initial desired size of x86_64 Ubuntu based nodes (CPU m6a.16xlarge)"
  type        = number
  default     = 0

  validation {
    condition     = var.ubuntu_x86_64_cpu_min_size >= 0
    error_message = "MUST: ubuntu_x86_64_cpu_min_size >=0"
  }
}

variable "ubuntu_x86_64_cpu_max_size" {
  description = "Max number of x86_64 Ubuntu based nodes (CPU m6a.16xlarge)"
  type        = number
  default     = 10

  validation {
    # we always want ubuntu CPU nodes thus enforce >0
    condition     = var.ubuntu_x86_64_cpu_max_size > 0
    error_message = "MUST: ubuntu_x86_64_cpu_min_size >0"
  }
}

variable "ubuntu_amis" {
  description = "Defines a set of custom AMIs for default managed node groups per region"
  type = map(object({
    x86_64_cpu = string
    x86_64_gpu = string
  }))

  default = {}
}

variable "mothership_rds_aurora_secret_arn" {
  description = "RDS Aurora secret ARN that is set up by mothership (single region for now)"
  type        = string
  default     = null
}

# maps each region to its ARN
variable "supabase_credential_secret_arns" {
  description = "Supabase credential secret ARNs that are manually set up at AWS account level (can be multi-region)"
  type        = map(any)
  default     = {}
}

variable "rds_aurora_host" {
  description = "RDS Aurora host"
  type        = string
  default     = null
}

variable "alertmanager_slack_channel" {
  description = "Name of the Slack channel to send alertmanager notifications to"
  type        = string
  default     = null
}

variable "alertmanager_slack_webhook_url" {
  description = "Webhook URL of the Slack channel for alertmanager notifications"
  type        = string
  default     = null
}

variable "alertmanager_target_namespaces" {
  type        = string
  description = "alertmanager target namespaces filter"
  default     = ".*"
}
