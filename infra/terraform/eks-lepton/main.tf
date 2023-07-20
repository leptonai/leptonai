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
      # do not "time_static.activation_date.unix" since it may diverge between plan/apply
      # truncate the seconds here, since it's only used for resource garbage collection
      LeptonClusterCreatedUnixTimeRFC3339 = formatdate("YYYY-MM-DD_hh-mm", time_static.activation_date.rfc3339)
    }
  }
}

data "aws_availability_zones" "available" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # decides partition (i.e., aws, aws-gov, aws-cn)
  partition = one(data.aws_partition.current[*].partition)
}

data "aws_iam_group" "dev_members" {
  group_name = "dev"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  regional_ubuntu_amis = lookup(var.ubuntu_amis, var.region, null)
}
