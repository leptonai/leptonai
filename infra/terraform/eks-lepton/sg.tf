resource "aws_security_group" "eks" {
  name_prefix = "${local.cluster_name}-cluster-sg"
  description = "Secondary EKS cluster security group to allow traffic from/to nodes"
  vpc_id      = module.vpc.vpc_id

  tags = {
    "Name" = "${local.cluster_name}-cluster-sg"
  }

  depends_on = [
    module.vpc
  ]
}

# required for managed node groups with "custom" AMIs to connect to EKS cluster
# not required for default EKS-provided AMIs
# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/node_groups.tf
resource "aws_security_group" "nodes" {
  name        = "${local.cluster_name}-nodes-sg"
  description = "Additional security group to attach to EKS managed node groups with custom AMIs"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    "Name" = "${local.cluster_name}-nodes-sg"
  }

  depends_on = [
    module.vpc,
    aws_security_group.eks
  ]
}

# ref. https://github.com/terraform-aws-modules/terraform-aws-eks/blob/master/node_groups.tf
locals {
  create_node_sg = true

  cluster_to_node_ingress_sg_rules = {
    ingress_node_ephemeral = {
      description = "Node to node ingress on ephemeral ports"
      protocol    = "tcp"
      from_port   = 1025
      to_port     = 65535
      type        = "ingress"
      self        = true
    }

    ingress_cluster_4443_webhook_metrics_server = {
      description                   = "Cluster API to node 4443/tcp webhook for metrics-server"
      protocol                      = "tcp"
      from_port                     = 4443
      to_port                       = 4443
      type                          = "ingress"
      source_cluster_security_group = true
    }

    ingress_cluster_6443_webhook_prometheus_adapter = {
      description                   = "Cluster API to node 6443/tcp webhook for prometheus-adapter"
      protocol                      = "tcp"
      from_port                     = 6443
      to_port                       = 6443
      type                          = "ingress"
      source_cluster_security_group = true
    }

    ingress_cluster_8443_webhook_karpenter = {
      description                   = "Cluster API to node 8443/tcp webhook for Karpenter"
      protocol                      = "tcp"
      from_port                     = 8443
      to_port                       = 8443
      type                          = "ingress"
      source_cluster_security_group = true
    }

    ingress_cluster_9443_webhook_alb = {
      description                   = "Cluster API to node 9443/tcp webhook for ALB controller, NGINX"
      protocol                      = "tcp"
      from_port                     = 9443
      to_port                       = 9443
      type                          = "ingress"
      source_cluster_security_group = true
    }

    ingress_cluster_443 = {
      description                   = "Cluster API to node groups"
      protocol                      = "tcp"
      from_port                     = 443
      to_port                       = 443
      type                          = "ingress"
      source_cluster_security_group = true
    }

    ingress_cluster_kubelet = {
      description                   = "Cluster API to node kubelets"
      protocol                      = "tcp"
      from_port                     = 10250
      to_port                       = 10250
      type                          = "ingress"
      source_cluster_security_group = true
    }

    ingress_self_coredns_tcp = {
      description = "Node to node CoreDNS"
      protocol    = "tcp"
      from_port   = 53
      to_port     = 53
      type        = "ingress"
      self        = true
    }

    ingress_self_coredns_udp = {
      description = "Node to node CoreDNS UDP"
      protocol    = "udp"
      from_port   = 53
      to_port     = 53
      type        = "ingress"
      self        = true
    }
  }
}

resource "aws_security_group_rule" "nodes" {
  for_each = { for k, v in local.cluster_to_node_ingress_sg_rules : k => v if local.create_node_sg }

  security_group_id = aws_security_group.nodes.id
  protocol          = each.value.protocol
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  type              = each.value.type

  description      = lookup(each.value, "description", null)
  cidr_blocks      = lookup(each.value, "cidr_blocks", null)
  ipv6_cidr_blocks = lookup(each.value, "ipv6_cidr_blocks", null)
  prefix_list_ids  = lookup(each.value, "prefix_list_ids", [])
  self             = lookup(each.value, "self", null)

  source_security_group_id = try(each.value.source_cluster_security_group, false) ? aws_security_group.eks.id : lookup(each.value, "source_security_group_id", null)

  depends_on = [
    module.vpc,
    aws_security_group.eks,
    aws_security_group.nodes
  ]
}

resource "aws_security_group_rule" "ingress_from_node_to_cluster" {
  description              = "Node to cluster ingress"
  protocol                 = "tcp"
  from_port                = 0
  to_port                  = 65535
  type                     = "ingress"
  security_group_id        = aws_security_group.eks.id
  source_security_group_id = aws_security_group.nodes.id

  depends_on = [
    module.vpc,
    aws_security_group.eks,
    aws_security_group.nodes,
    aws_security_group_rule.nodes
  ]
}
