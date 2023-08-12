# overwrites "LeptonClusterCreatedUnixTimeRFC3339" for AWS resource tagging
variable "created_unix_time_rfc3339" {
  description = "Cluster created unix time in RFC3339 format with hour precision"
  type        = string
  default     = "2023-08-05T00"
}

variable "deployment_environment" {
  description = "Deployment environment; DEV, or PROD"
  type        = string
  default     = "DEV"

  validation {
    condition     = contains(["DEV", "PROD"], var.deployment_environment)
    error_message = "Valid 'deployment_environment' values are DEV, or PROD"
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

# cloud.lepton.ai: Z007822916VK7B4DFVMP7 is used in DEV  account (account# 605454121064)
# app.lepton.ai: Z0305788EACPTSFEJARC is used in PROD account (account# 720771144610)
variable "lepton_cloud_route53_zone_id" {
  description = "root hostname Route53 zone ID"
  type        = string
  default     = "Z007822916VK7B4DFVMP7"
}

# cloud.lepton.ai: Z007822916VK7B4DFVMP7 is used in DEV  account (account# 605454121064)
# app.lepton.ai: Z0305788EACPTSFEJARC is used in PROD account (account# 720771144610)
variable "root_hostname" {
  description = "Root hostname"
  type        = string
  default     = "cloud.lepton.ai"
}

# d8d5e0e1-ecc5-4716-aa79-01625e60704d in DEV account (cloud.lepton.ai, account# 605454121064)
# 6767482b-dfe1-4802-afe4-408df40a264a in PROD account (app.lepton.ai, account# 720771144610)
variable "tls_cert_arn_id" {
  description = "TLS certificate ARN ID"
  type        = string
  default     = "d8d5e0e1-ecc5-4716-aa79-01625e60704d"
}

variable "shared_alb_route53_zone_id" {
  description = "shared alb root hostname Route53 zone ID"
  type        = string
  default     = ""
}

variable "shared_alb_root_hostname" {
  description = "Root hostname for shared alb based routing"
  type        = string
  default     = ""
}

variable "aurora_master_username" {
  description = "Username for the Aurora master DB user. Required unless `snapshot_identifier` or `replication_source_identifier` is provided or unless a `global_cluster_identifier` is provided when the cluster is the secondary cluster of a global database"
  type        = string
  default     = "root"
}

variable "api_token_key" {
  description = "Mothership API token key used for AWS secret manager"
  type        = string
  default     = "mothership_api_token"
}

variable "api_token" {
  description = "API token for auth"
  type        = string
  default     = ""
}

variable "mothership_role_name" {
  description = "The name of AWS IAM role for mothership"
  type        = string
  default     = "mothership-role"
}
