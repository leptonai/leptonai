# See https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering

# default AMI from https://cloud-images.ubuntu.com/docs/aws/eks also works
# but it does not come with necessary add-ons such as GPU driver
ubuntu_amis = {
  "us-east-1" : {
    # custom built with pre-fetched Lepton images
    x86_64_cpu = "ami-04b8af3864f78166e",

    # custom built to install NVIDIA drivers with pre-fetched Lepton images
    # image is built using g4dn instance with NVIDIA T4 chip
    # but works with other instance types
    # since upstream NVIDIA driver is the same
    x86_64_gpu = "ami-0b10f260913ad7e15"
  }
}
