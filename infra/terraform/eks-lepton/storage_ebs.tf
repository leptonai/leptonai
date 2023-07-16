module "ebs_csi_driver_irsa" {
  source                = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version               = "~> 5.14"
  role_name             = format("%s-%s", local.cluster_name, "ebs-csi-driver")
  attach_ebs_csi_policy = true
  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}

# https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
resource "aws_eks_addon" "csi_ebs" {
  cluster_name = module.eks.cluster_name

  # ref. "aws eks describe-addon-versions --kubernetes-version 1.26"
  addon_name    = "aws-ebs-csi-driver"
  addon_version = "v1.20.0-eksbuild.1"

  # TODO: define resolve_conflicts
  # resolve_conflicts_on_create = "OVERWRITE"
  # resolve_conflicts_on_update = "OVERWRITE"

  # whether to preserve the created resources when deleting the EKS add-on
  preserve = false

  service_account_role_arn = module.ebs_csi_driver_irsa.iam_role_arn

  depends_on = [
    module.eks,
    module.ebs_csi_driver_irsa
  ]
}
