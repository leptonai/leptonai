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

  # TODO: make prom server volume ephemeral storage and write to remote storage
  # currently running with a pvc with only two replicas
  # pod deployed to a different az will not work
  #
  # aws eks describe-addon-configuration --addon-name kubecost_kubecost --addon-version v1.103.3-eksbuild.0
  # https://docs.aws.amazon.com/cli/latest/reference/eks/describe-addon-configuration.html
  # https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon#example-add-on-usage-with-custom-configuration_values
  # configuration_values = jsonencode({
  # })

  depends_on = [
    module.eks
  ]
}
