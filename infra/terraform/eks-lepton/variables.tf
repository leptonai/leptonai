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
