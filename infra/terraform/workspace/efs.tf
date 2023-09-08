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
  throughput_mode = "elastic"

  access_points = {
    non_root = {
      name = "non_root"
      posix_user = {
        gid = 65534
        uid = 65534
      }
      root_directory = {
        path = "/lepton_non_root"
        creation_info = {
          owner_gid   = 65534
          owner_uid   = 65534
          permissions = "755"
        }
      }
    }
  }
}
