# https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
# https://docs.aws.amazon.com/prometheus/latest/userguide/integrating-kubecost.html
# https://docs.kubecost.com/install-and-configure/install/provider-installations/aws-eks-cost-monitoring
resource "aws_eks_addon" "kubecost" {
  cluster_name = module.eks.cluster_name

  # ref. "aws eks describe-addon-versions --kubernetes-version 1.26"
  addon_name    = "kubecost_kubecost"
  addon_version = "v1.103.3-eksbuild.0"

  # TODO: define resolve_conflicts
  # resolve_conflicts_on_create = "OVERWRITE"
  # resolve_conflicts_on_update = "OVERWRITE"

  # whether to preserve the created resources when deleting the EKS add-on
  preserve = false

  depends_on = [
    module.eks
  ]
}
