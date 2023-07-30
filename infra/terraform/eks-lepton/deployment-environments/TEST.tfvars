# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment    = "TEST"
auth_users_iam_group_name = "dev"

region = "us-east-1"

default_capacity_type         = "SPOT"
cpu_node_group_instance_types = ["t3.xlarge", "c5.xlarge"]

single_nat_gateway = true

# must be >= AMI snapshot size
disk_size_in_gb_for_node_groups = 100

lepton_cloud_route53_zone_id = "Z007822916VK7B4DFVMP7"

# default AMI from https://cloud-images.ubuntu.com/docs/aws/eks also works
# but it does not come with necessary add-ons such as GPU driver
ubuntu_amis = {
  "us-east-1" : {
    # custom built with pre-fetched Lepton images
    x86_64_cpu = "ami-0fb2155d0930fa381",

    # custom built to install NVIDIA drivers with pre-fetched Lepton images
    # image is built using g4dn instance with NVIDIA T4 chip
    # but works with other instance types
    # since upstream NVIDIA driver is the same
    x86_64_gpu = "ami-0f5cfba4a72f3af0d"
  }
}

use_ubuntu_nvidia_gpu_operator = true

al2_x86_64_ac_g4dnxlarge_min_size = 0
al2_x86_64_ac_g4dnxlarge_max_size = 1
al2_x86_64_ac_g52xlarge_min_size  = 0
al2_x86_64_ac_g52xlarge_max_size  = 1
al2_x86_64_cpu_min_size           = 0
al2_x86_64_cpu_max_size           = 1

ubuntu_x86_64_ac_g4dnxlarge_min_size = 0
ubuntu_x86_64_ac_g4dnxlarge_max_size = 1
ubuntu_x86_64_ac_g52xlarge_min_size  = 0
ubuntu_x86_64_ac_g52xlarge_max_size  = 1
ubuntu_x86_64_cpu_min_size           = 3 # run more nodes since we are using small instance types
ubuntu_x86_64_cpu_max_size           = 10
