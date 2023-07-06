terraform {
  cloud {
    organization = "lepton"
    hostname     = "app.terraform.io"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.67.0"
    }
  }

  required_version = "~> 1.3"
}
