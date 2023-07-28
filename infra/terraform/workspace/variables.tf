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

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Cluster name"
  type        = string
  default     = "dev-ci"
}

variable "oidc_id" {
  description = "OIDC ID"
  type        = string
  default     = "B39F84C46B64A666C6BCF2E155312E98"
}

variable "tls_cert_arn_id" {
  description = "TLS certificate ARN ID"
  type        = string
  default     = "d8d5e0e1-ecc5-4716-aa79-01625e60704d"
}

variable "root_domain" {
  description = "Root domain"
  type        = string
  default     = "cloud.lepton.ai"
}

variable "workspace_name" {
  description = "Workspace name"
  type        = string
  default     = "dev"
}

variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
  default     = "dev"
}

variable "api_token" {
  description = "API token for auth"
  type        = string
  default     = ""
}

variable "lepton_web_enabled" {
  description = "Whether to install Lepton web"
  type        = bool
  default     = true
}

variable "lepton_api_server_enable_tuna" {
  description = "Whether to enable tuna for the api server"
  type        = bool
  default     = true
}

variable "image_tag_web" {
  description = "Image tag for web"
  type        = string
  default     = "latest"
}

variable "image_tag_api_server" {
  description = "Image tag for the api server"
  type        = string
  default     = "latest"
}

variable "image_tag_deployment_operator" {
  description = "Image tag for the operator"
  type        = string
  default     = "latest"
}

variable "create_efs" {
  description = "Whether to create a EFS"
  type        = bool
  default     = false
}

variable "efs_mount_targets" {
  type = map(object({
    subnet_id = string
  }))
  description = "Map of mount targets for EFS"
  default     = {}
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
  default     = "vpc-0a0b0c0d0e0f0g0h0"
}

variable "enable_quota" {
  description = "Enable quota"
  type        = bool
  default     = true
}

variable "quota_cpu" {
  description = "Quota limit for CPU"
  type        = number
  default     = 5
}

variable "quota_memory" {
  description = "Quota limit for memory"
  type        = number
  default     = 17
}

variable "quota_gpu" {
  description = "Quota limit for GPU"
  type        = number
  default     = 1
}

variable "state" {
  description = "Workspace state (normal, paused, terminated)"
  type        = string
  default     = "normal"
}
