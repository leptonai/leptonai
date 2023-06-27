module "efs" {
  source = "terraform-aws-modules/efs/aws"

  count = var.create_efs ? 1 : 0

  name          = "efs-lepton-${var.workspace_name}"
  mount_targets = var.efs_mount_targets

  security_group_description = "${var.workspace_name} EFS security group"
  security_group_vpc_id      = var.vpc_id
  security_group_rules = {
    vpc = {
      # relying on the defaults provdied for EFS/NFS (2049/TCP + ingress)
      description = "NFS ingress from VPC private subnets"
      cidr_blocks = ["10.0.0.0/16"]
    }
  }
  // TODO: explore how to set it to true
  deny_nonsecure_transport = false
  attach_policy            = false
  # TODO: add tags

  access_points = {
    non_root = {
      name = "non_root"
      posix_user = {
        gid            = 1000
        uid            = 1000
      }
      root_directory = {
        path = "/lepton_non_root"
        creation_info = {
          owner_gid   = 1000
          owner_uid   = 1000
          permissions = "755"
        }
      }
    }
  }
}
