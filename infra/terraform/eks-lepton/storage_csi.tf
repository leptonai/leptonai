#---------------------------------------------------------------
# GP3 Storage Class
#---------------------------------------------------------------
# This is required since intree CSI driver does not support gp3.
# Create "gp3" as default first, and later update/replace the existing "gp2".
# ref. https://github.com/leptonai/lepton/pull/532
# ref. https://aws.amazon.com/blogs/containers/amazon-ebs-csi-driver-is-now-generally-available-in-amazon-eks-add-ons/
# ref. https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/storage_class_v1
resource "kubernetes_storage_class_v1" "gp3_sc_default" {
  metadata {
    name = "gp3"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "true"
    }
  }

  storage_provisioner    = "ebs.csi.aws.com"
  reclaim_policy         = "Delete"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type      = "gp3"
    fsType    = "ext4"
    encrypted = "true"
  }
}

resource "kubernetes_storage_class_v1" "efs_sc" {
  metadata {
    name = "efs-sc"
  }

  storage_provisioner = "efs.csi.aws.com"
}

# make it non-default
# NOTE: "gp2" must be deleted first, before updating
# [parameters: Forbidden: updates to parameters are forbidden., provisioner: Forbidden: updates to provisioner are forbidden.]
# ref. https://github.com/hashicorp/terraform-provider-kubernetes/issues/723#issuecomment-1141833527
# ref. https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/storage_class_v1
#
# TODO
# right now we only patch, so the default encryption is "false"
# use kubernetes job to update other volume parameters
# ref. https://github.com/hashicorp/terraform-provider-kubernetes/issues/723#issuecomment-1278285213
resource "kubernetes_annotations" "gp2_sc_non_default" {
  api_version = "storage.k8s.io/v1"
  kind        = "StorageClass"
  force       = "true"

  metadata {
    name = "gp2"
  }
  annotations = {
    "storageclass.kubernetes.io/is-default-class" = "false"
  }
}

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
