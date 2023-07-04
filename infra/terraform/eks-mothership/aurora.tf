# https://github.com/terraform-aws-modules/terraform-aws-rds-aurora
module "aurora" {
  source = "terraform-aws-modules/rds-aurora/aws"

  name          = "${local.cluster_name}-aurora-postgresql"
  database_name = "postgres"

  engine         = "aurora-postgresql"
  engine_version = "14.7"

  storage_type = "aurora-iopt1"
  instances = {
    1 = {
      instance_class      = "db.r5.large"
      publicly_accessible = true
    }
  }

  autoscaling_enabled      = true
  autoscaling_min_capacity = 1
  autoscaling_max_capacity = 3

  vpc_id = module.vpc.vpc_id

  # password stored in secret manager
  manage_master_user_password = true
  master_username             = var.aurora_master_username

  create_db_subnet_group = true

  # use public subnet for external access (e.g., dev testing)
  subnets = module.vpc.public_subnets

  create_security_group = true
  security_group_rules = {
    # allow access within VPC
    vpc_ingress = {
      cidr_blocks = module.vpc.public_subnets_cidr_blocks
    }
  }

  storage_encrypted = true
  apply_immediately = true

  create_cloudwatch_log_group            = true
  cloudwatch_log_group_retention_in_days = 7

  enabled_cloudwatch_logs_exports = ["postgresql"]
  monitoring_interval             = 60

  tags = {
    Environment = "mothership"
    Terraform   = "true"
  }

  depends_on = [
    module.vpc
  ]
}
