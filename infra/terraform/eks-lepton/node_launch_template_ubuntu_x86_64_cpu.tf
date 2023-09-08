# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/launch_template
# https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/modules/eks-managed-node-group/main.tf
resource "aws_launch_template" "ubuntu_x86_64_cpu" {
  name_prefix = "${var.cluster_name}-ubuntu-x86_64-cpu-"
  image_id    = local.regional_ubuntu_amis.x86_64_cpu

  vpc_security_group_ids = [
    # https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest
    module.eks.cluster_primary_security_group_id,

    # required for managed node groups with "custom" AMIs to connect to EKS cluster
    # not required for default EKS-provided AMIs
    # TODO: check if we can replace this with "module.eks.vpc_config.cluster_security_group_id"
    aws_security_group.nodes.id,
  ]

  # Disk size must be specified within the launch template
  # not in "aws_launch_template", otherwise fail...
  block_device_mappings {
    device_name = "/dev/sda1"

    # https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/launch_template#ebs
    ebs {
      volume_type           = "gp3"
      volume_size           = var.disk_size_in_gb_for_node_groups
      iops                  = 3000
      encrypted             = true
      delete_on_termination = true
      throughput            = 125
    }
  }

  # Whether to update Default Version each update
  # "eks-managed-node-group" "var.update_launch_template_default_version" is set to true by default
  update_default_version = true

  # TODO: currently defaults, harden this
  # TODO: https://github.com/leptonai/lepton/pull/874
  # https://stackoverflow.com/questions/66069187/is-it-possible-to-prevent-a-kubernetes-pod-on-eks-from-assuming-the-nodes-iam-r
  # https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/launch_template#metadata-options
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "optional" # TODO: change this to "required"
    http_put_response_hop_limit = 2          # TODO: change this to 1
    instance_metadata_tags      = "disabled"
  }

  # "eks-managed-node-group" "var.enable_monitoring" is set to true by default
  monitoring {
    enabled = true
  }

  # "eks-managed-node-group" "var.tag_specifications" is set to
  # ["instance", "volume", "network-interface"] by default
  tag_specifications {
    resource_type = "instance"
    tags = {
      "Name" = var.cluster_name
    }
  }
  tag_specifications {
    resource_type = "volume"
    tags = {
      "Name" = var.cluster_name
    }
  }
  tag_specifications {
    resource_type = "network-interface"
    tags = {
      "Name" = var.cluster_name
    }
  }

  # By default, EKS managed node groups will not append bootstrap script;
  # this adds it back in using the default template provided by the module
  # Note: this assumes the AMI provided is an EKS optimized AMI derivative
  # that has the "/etc/eks/bootstrap.sh" file
  user_data = base64encode(<<-SCRIPT
    #!/bin/bash
    set -e
    set -x

    # https://github.com/awslabs/amazon-eks-ami/blob/master/files/bootstrap.sh
    # will fetch B64_CLUSTER_CA and APISERVER_ENDPOINT if not specified
    /etc/eks/bootstrap.sh ${var.cluster_name} \
    --b64-cluster-ca '${module.eks.cluster_certificate_authority_data}' \
    --apiserver-endpoint '${module.eks.cluster_endpoint}'
    SCRIPT
  )

  depends_on = [
    module.vpc,
    aws_security_group.eks,
    aws_security_group.nodes,
    aws_iam_role_policy_attachment.mng_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.mng_AmazonEC2ContainerRegistryReadOnly,
    aws_iam_role_policy_attachment.mng_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.mng_AmazonSSMFullAccess,
    aws_iam_role_policy_attachment.csi_efs_node,
    module.eks
  ]

  lifecycle {
    create_before_destroy = true
  }
}
