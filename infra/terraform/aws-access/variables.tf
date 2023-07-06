variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["prod", "dev"], var.environment)
    error_message = "Valid 'environment' values are prod or dev"
  }
}

variable "admin_users" {
  description = "List of admin user names to create"
  type        = list(string)
  default     = []
}

variable "power_users" {
  description = "List of limited write user names to create"
  type        = list(string)
  default     = []
}

variable "read_only_users" {
  description = "List of read-only user names to create"
  type        = list(string)
  default     = []
}

variable "account_ids" {
  description = "Defines a set of AWS account IDs"
  type        = map(any)
  default     = {}
}
