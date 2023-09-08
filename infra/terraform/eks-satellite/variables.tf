# overwrites "LeptonClusterUpdatedUnixTimeRFC3339" for AWS resource tagging
variable "updated_unix_time_rfc3339" {
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

variable "satellite_name" {
  description = "Satellite name"
  type        = string
  default     = null
}

variable "satellite_node_user_arn" {
  description = "AWS IAM user ARN for assuming satellite nodes"
  type        = string
  default     = null
}
