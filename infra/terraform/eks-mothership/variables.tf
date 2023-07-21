variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "Account ID"
  type        = string
  default     = "605454121064"
}

variable "cluster_name" {
  description = "Cluster name"
  type        = string
  default     = null
}

variable "lepton_cloud_route53_zone_id" {
  description = "root hostname Route53 zone ID"
  type        = string
  default     = "Z007822916VK7B4DFVMP7"
}

variable "root_hostname" {
  description = "Root hostname"
  type        = string
  default     = "cloud.lepton.ai"
}

variable "aurora_master_username" {
  description = "Username for the Aurora master DB user. Required unless `snapshot_identifier` or `replication_source_identifier` is provided or unless a `global_cluster_identifier` is provided when the cluster is the secondary cluster of a global database"
  type        = string
  default     = "root"
}

variable "tls_cert_arn_id" {
  description = "TLS certificate ARN ID"
  type        = string
  default     = "d8d5e0e1-ecc5-4716-aa79-01625e60704d"
}
