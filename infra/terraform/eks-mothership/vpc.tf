locals {
  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)
}

# https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "vpc-${local.cluster_name}"

  cidr = local.vpc_cidr
  azs  = local.azs

  # VPC CIDR 10.0.0.0/16 ranges from 10.0.0.0 to 10.0.255.255 with 65534 IPs.
  #
  # We need more private subnets since we can just deploy load balancers in public subnets
  # and still route traffic to pods in private subnets.
  # ref. https://docs.aws.amazon.com/eks/latest/userguide/creating-a-vpc.html
  #
  # e.g., a reigon of 4 AZs will have:
  # 10.0.0.0/20  from 10.0.0.0  to 10.0.15.255 with 4094 IPs.
  # 10.0.16.0/20 from 10.0.16.0 to 10.0.31.255 with 4094 IPs.
  # 10.0.32.0/20 from 10.0.32.0 to 10.0.47.255 with 4094 IPs.
  # 10.0.48.0/20 from 10.0.48.0 to 10.0.63.255 with 4094 IPs.
  # ref. https://developer.hashicorp.com/terraform/language/functions/cidrsubnet
  private_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 4, k)]
  #
  # e.g., a reigon of 4 AZs will have:
  # 10.0.60.0/24 from 10.0.60.0 to 10.0.60.255 with 254 IPs.
  # 10.0.61.0/24 from 10.0.61.0 to 10.0.61.255 with 254 IPs.
  # 10.0.62.0/24 from 10.0.62.0 to 10.0.62.255 with 254 IPs.
  # 10.0.63.0/24 from 10.0.63.0 to 10.0.63.255 with 254 IPs.
  #
  # NOTE: use 60 to avoid CIDR range conflicts in a region of >=4 AZs.
  # ref. https://developer.hashicorp.com/terraform/language/functions/cidrsubnet
  public_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 60)]

  enable_nat_gateway = true

  # do not "single_nat_gateway = true"
  # and use the default "single_nat_gateway = false"
  # to create NAT gateway in each AZ for higher availability
  # cross-AZ data transfer bill is not that much...

  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                      = 1
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"             = 1
  }
}
