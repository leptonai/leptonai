resource "helm_release" "mothership" {
  name = "mothership"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "charts/mothership"

  namespace = "default"

  set {
    name  = "mothership.image.repository"
    value = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/lepton-mothership"
  }

  # TODO: create the role using terraform
  set {
    name  = "mothership.serviceAccountRoleArn"
    value = "arn:${local.partition}:iam::${var.account_id}:role/mothership-role"
  }

  set {
    name  = "mothership.apiToken"
    value = var.api_token
  }

  set {
    name  = "mothership.certificateArn"
    value = "arn:${local.partition}:acm:${var.region}:${var.account_id}:certificate/${var.tls_cert_arn_id}"
  }

  set {
    name  = "mothership.hostname"
    value = "mothership.${var.root_hostname}"
  }

  depends_on = [
    module.vpc,
    module.eks,
    helm_release.alb_controller,
    helm_release.external_dns,
  ]
}
