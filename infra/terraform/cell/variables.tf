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

variable "account_id" {
  description = "Account ID"
  type        = string
  default     = "605454121064"
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

variable "cell_name" {
  description = "Cell name"
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
