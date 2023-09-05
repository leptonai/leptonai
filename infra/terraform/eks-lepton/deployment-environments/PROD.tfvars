# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment    = "PROD"
auth_users_iam_group_name = "prod-admins"

# different AWS account for prod: 720771144610
# default region with the most capacity
region = "us-west-2"

default_capacity_type = "ON_DEMAND"

# 64 vCPUs + 256 GiB RAM
# ref. https://aws.amazon.com/ec2/instance-types/m6a/
cpu_node_group_instance_types = ["m6a.16xlarge"]

# for maximum availability
single_nat_gateway = false

# must be >= AMI snapshot size
disk_size_in_gb_for_node_groups = 1000

lepton_cloud_route53_zone_id = "Z0305788EACPTSFEJARC"

# default AMI from https://cloud-images.ubuntu.com/docs/aws/eks also works
# but it does not come with necessary add-ons such as GPU driver
# see https://github.com/leptonai/lepton/blob/main/infra/terraform/eks-lepton/README.amis.md for latest
ubuntu_amis = {
  "us-west-2" : {
    # custom built with pre-fetched Lepton images
    x86_64_cpu = "ami-086eaf7fcdadfa0f8",

    # custom built to install NVIDIA drivers with pre-fetched Lepton images
    # image is built using g4dn instance with NVIDIA T4 chip
    # but works with other instance types
    # since upstream NVIDIA driver is the same
    x86_64_gpu = "ami-072faa66fd0b86a90"
  },

  # TODO: remove this after us-east-1 is cleaned up
  "us-east-1" : {
    x86_64_cpu = "ami-00000000000000000",
    x86_64_gpu = "ami-00000000000000000"
  }
}

use_ubuntu_nvidia_gpu_operator = true

# use min size as the desired capacity for AWS EKS node groups
# in case of ubuntu node bugs, we can do tf apply/update
# to create fallback node groups with >0 desired/max capacity
# do not set "max_size" to >0, otherwise cluster autoscaler
# will read the launch template and scale up the node groups
al2_x86_64_ac_g4dnxlarge_min_size = 0
al2_x86_64_ac_g4dnxlarge_max_size = 0
al2_x86_64_ac_g52xlarge_min_size  = 0
al2_x86_64_ac_g52xlarge_max_size  = 0
al2_x86_64_cpu_min_size           = 0
al2_x86_64_cpu_max_size           = 0

# use min size as the desired capacity for AWS EKS node groups
# start with 0 nodes for GPU node groups
# let cluster autoscaler scale up on demand
ubuntu_x86_64_ac_g4dnxlarge_min_size = 1
ubuntu_x86_64_ac_g4dnxlarge_max_size = 8
ubuntu_x86_64_ac_g52xlarge_min_size  = 1
ubuntu_x86_64_ac_g52xlarge_max_size  = 16
ubuntu_x86_64_cpu_min_size           = 1
ubuntu_x86_64_cpu_max_size           = 6

mothership_rds_aurora_secret_arn = "arn:aws:secretsmanager:us-west-2:720771144610:secret:rds!cluster-ad702e1c-d2ab-4fa2-abdd-44d1849b806c-DZWYM6"
supabase_credential_secret_arns = {
  "us-west-2" : "arn:aws:secretsmanager:us-west-2:720771144610:secret:supabase_credential-MWpY4D"
}

# aurora host for prod database
rds_aurora_host = "mothership-prod-aws-us-west-2-aurora-postgresql-1.cym32vh4eh2e.us-west-2.rds.amazonaws.com"

# TODO: change to prod channel
# ref. https://grafana.com/blog/2020/02/25/step-by-step-guide-to-setting-up-prometheus-alertmanager-with-slack-pagerduty-and-gmail/
alertmanager_slack_channel     = "#alertmanager-test"
alertmanager_slack_webhook_url = "https://hooks.slack.com/services/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"
alertmanager_target_namespaces = ".*"
