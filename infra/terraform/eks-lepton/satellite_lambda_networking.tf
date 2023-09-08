# NOTE: we create this outside of the VPC module,
# because EKS API does not support updating the VPC configuration subnet IDs.
# Mostly copied from https://github.com/terraform-aws-modules/terraform-aws-vpc/blob/master/main.tf.

locals {
  # NOTE: This CIDR DOES NOT overlap with existing EKS VPC CIDR ranges!
  # We need non-overlapping CIDR for satellite nodes for custom route rules.
  # See https://github.com/leptonai/lepton/issues/2935 for more contexts.
  # 10.0.80.0/20 from 10.0.80.0 to 10.0.95.255 with 4094 IPs.
  satellite_lambda_cidr_block_az_0 = "10.0.80.0/20"

  # Using the same default for existing subnet routes.
  satellite_lambda_nat_gateway_destination_cidr_block = "0.0.0.0/0"
}

# to reserve non-overlapping CIDR ranges for satellite nodes
# we need to create a separate subnet for satellite nodes
# just because EKS API does not support updating the VPC configuration subnet IDs
# which makes it impossible to add a new subnet to existing EKS
# ref. https://github.com/leptonai/lepton/issues/2935
# ref. https://github.com/aws/containers-roadmap/issues/170#issuecomment-780174859
# ref. https://registry.terraform.io/providers/-/aws/latest/docs/resources/subnet
resource "aws_subnet" "satellite_lambda_az_0" {
  vpc_id            = module.vpc.vpc_id
  availability_zone = local.azs[0]
  cidr_block        = local.satellite_lambda_cidr_block_az_0

  tags = {
    Name = "vpc-${local.cluster_name}-private-${local.azs[0]}-satellite-lambda"

    # MUST BE TAGGED WITH CLUSTER NAME for satellite nodes to join the EKS
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                      = 1
  }
}

# ref. https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table.html
resource "aws_route_table" "satellite_lambda" {
  vpc_id = module.vpc.vpc_id

  tags = {
    Name = "vpc-${local.cluster_name}-private-satellite-lambda"
  }
}

# ref. https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association.html
resource "aws_route_table_association" "satellite_lambda_az_0" {
  subnet_id      = aws_subnet.satellite_lambda_az_0.id
  route_table_id = aws_route_table.satellite_lambda.id
}

# ref. https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest#output_natgw_ids
# ref. https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route.html
resource "aws_route" "satellite_lambda_nat_gateway" {
  count = length(module.vpc.natgw_ids)

  route_table_id         = aws_route_table.satellite_lambda.id
  destination_cidr_block = local.satellite_lambda_nat_gateway_destination_cidr_block
  nat_gateway_id         = element(module.vpc.natgw_ids[*], count.index)

  timeouts {
    create = "5m"
  }
}
