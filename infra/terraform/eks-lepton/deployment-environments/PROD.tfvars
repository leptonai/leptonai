# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment    = "PROD"
auth_users_iam_group_name = "prod-admins"

region = "us-west-2"

default_capacity_type         = "ON_DEMAND"
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
    x86_64_cpu = "ami-0dfcb28cf6bf4142f",

    # custom built to install NVIDIA drivers with pre-fetched Lepton images
    # image is built using g4dn instance with NVIDIA T4 chip
    # but works with other instance types
    # since upstream NVIDIA driver is the same
    x86_64_gpu = "ami-0525c008f4e0dee62"
  },

  # TODO: remove this after us-east-1 is cleaned up
  "us-east-1" : {
    x86_64_cpu = "ami-00000000000000000",
    x86_64_gpu = "ami-00000000000000000"
  }
}

use_ubuntu_nvidia_gpu_operator = true

# create node groups with zero desired capacity as fallback
al2_x86_64_ac_g4dnxlarge_min_size = 0
al2_x86_64_ac_g4dnxlarge_max_size = 1
al2_x86_64_ac_g52xlarge_min_size  = 0
al2_x86_64_ac_g52xlarge_max_size  = 1
al2_x86_64_cpu_min_size           = 0
al2_x86_64_cpu_max_size           = 1

ubuntu_x86_64_ac_g4dnxlarge_min_size = 1
ubuntu_x86_64_ac_g4dnxlarge_max_size = 8
ubuntu_x86_64_ac_g52xlarge_min_size  = 1
ubuntu_x86_64_ac_g52xlarge_max_size  = 8
ubuntu_x86_64_cpu_min_size           = 1
ubuntu_x86_64_cpu_max_size           = 4

mothership_rds_aurora_secret_arn = "arn:aws:secretsmanager:us-west-2:720771144610:secret:rds!cluster-ad702e1c-d2ab-4fa2-abdd-44d1849b806c-DZWYM6"
supabase_credential_secret_arns = {
  "us-west-2" : "arn:aws:secretsmanager:us-west-2:720771144610:secret:supabase_credential-MWpY4D"
}
