# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment = "PROD"
region                 = "us-west-2"

default_capacity_type = "ON_DEMAND"

# for maximum availability
single_nat_gateway = false

# must be >= AMI snapshot size
disk_size_in_gb_for_node_groups = 1000

# default AMI from https://cloud-images.ubuntu.com/docs/aws/eks also works
# but it does not come with necessary add-ons such as GPU driver
# see https://github.com/leptonai/lepton/blob/main/infra/terraform/eks-lepton/README.amis.md for latest
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

al2_x86_64_ac_g4dnxlarge_min_size   = 0
al2_x86_64_ac_g4dnxlarge_max_size   = 1
al2_x86_64_ac_g52xlarge_min_size    = 0
al2_x86_64_ac_g52xlarge_max_size    = 1
al2_x86_64_cpu_m6a16xlarge_min_size = 0
al2_x86_64_cpu_m6a16xlarge_max_size = 1

ubuntu_x86_64_ac_g4dnxlarge_min_size   = 1
ubuntu_x86_64_ac_g4dnxlarge_max_size   = 8
ubuntu_x86_64_ac_g52xlarge_min_size    = 1
ubuntu_x86_64_ac_g52xlarge_max_size    = 8
ubuntu_x86_64_cpu_m6a16xlarge_min_size = 1
ubuntu_x86_64_cpu_m6a16xlarge_max_size = 4
