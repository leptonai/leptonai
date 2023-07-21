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

variable "aurora_master_username" {
  description = "Username for the Aurora master DB user. Required unless `snapshot_identifier` or `replication_source_identifier` is provided or unless a `global_cluster_identifier` is provided when the cluster is the secondary cluster of a global database"
  type        = string
  default     = "root"
}
