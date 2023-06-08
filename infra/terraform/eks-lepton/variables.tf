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

variable "lepton_api_server_name" {
  description = "Lepton API server name"
  type        = string
  default     = "lepton-api-server"
}

variable "lepton_web_enabled" {
  description = "Whether to install Lepton web"
  type        = bool
  default     = true
}

variable "lepton_web_name" {
  description = "Lepton web name"
  type        = string
  default     = "lepton-web"
}

variable "lepton_namespace" {
  description = "Lepton namespace"
  type        = string
  default     = "default"
}

variable "lepton_cloud_route53_zone_id" {
  description = "cloud.lepton.ai Route53 zone ID"
  type        = string
  default     = "Z007822916VK7B4DFVMP7"
}

variable "api_token" {
  description = "API token for auth"
  type        = string
  default     = ""
}
