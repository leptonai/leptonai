# https://registry.terraform.io/providers/hashicorp/time/latest/docs
resource "time_static" "activation_date" {}

provider "aws" {
  region = var.region

  # ref. https://registry.terraform.io/providers/hashicorp/aws/latest/docs#default_tags-configuration-block
  default_tags {
    tags = {
      LeptonResourceKind = "eks-lepton"

      # used for garbage collection routines
      # TEST: may be destroyed within hours of creation
      # DEV: may be destroyed within 10 days of creation (with notice)
      # PROD: destroy should never be automated
      LeptonDeploymentEnvironment = var.deployment_environment

      LeptonClusterName = local.cluster_name

      # created time
      # https://registry.terraform.io/providers/hashicorp/time/latest/docs
      LeptonClusterCreatedUnixSecond      = time_static.activation_date.unix
      LeptonClusterCreatedUnixTimeRFC3339 = formatdate("YYYY-MM-DD_hh-mm-ss", time_static.activation_date.rfc3339)
    }
  }
}

data "aws_availability_zones" "available" {}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

data "aws_iam_group" "dev_members" {
  group_name = "dev"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}
