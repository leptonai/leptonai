# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment = "TEST"

# default region with the most capacity
region = "us-east-1"

# this is already created in the account
satellite_node_user_arn = "arn:aws:iam::605454121064:user/satellite-node"
