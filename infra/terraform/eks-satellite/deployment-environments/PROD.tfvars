# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment = "PROD"

# different AWS account for prod: 720771144610
# default region with the most capacity
region = "us-west-2"

# this is already created in the account
satellite_node_user_arn = "arn:aws:iam::720771144610:user/satellite-node"
