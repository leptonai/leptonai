module "efs" {
  source = "terraform-aws-modules/efs/aws"

  count = var.create_efs ? 1 : 0

  name          = "efs-lepton-${var.cell_name}"
  mount_targets = var.efs_mount_targets

  # TODO: create a security group for EFS
  create_security_group = false

  # TODO: add tags
}
