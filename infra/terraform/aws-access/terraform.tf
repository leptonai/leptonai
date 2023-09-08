terraform {
  cloud {
    organization = "lepton"
    hostname     = "app.terraform.io"
  }

  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }

  required_version = "~> 1.3"
}
