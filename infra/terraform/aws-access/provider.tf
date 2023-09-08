provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # decides partition (i.e., aws, aws-gov, aws-cn)
  partition = one(data.aws_partition.current[*].partition)
}
