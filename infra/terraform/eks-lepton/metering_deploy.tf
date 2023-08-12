resource "helm_release" "lepton_metering" {
  name = "lepton-metering"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/metering"

  namespace = "metering"

  set {
    name  = "metering.syncEnabled"
    value = true
  }

  set {
    name  = "metering.aggregateEnabled"
    value = true
  }

  set {
    name  = "metering.backfillEnabled"
    value = true
  }

  set {
    name  = "metering.auroraDbHost"
    value = var.rds_aurora_host
  }

  set {
    name  = "metering.region"
    value = var.region
  }

  set {
    name  = "metering.image.repository"
    value = "${local.account_id}.dkr.ecr.${var.region}.amazonaws.com/lepton-mothershipctl"
  }

  depends_on = [
    module.eks,
    module.vpc,
    kubernetes_config_map_v1_data.aws_auth,
    helm_release.alb_controller,
    helm_release.kubecost,
  ]
}
