resource "helm_release" "lepton" {
  name = "lepton"

  # here, we assume the running script or mothership(controller)
  # copies the whole directory in the same directory tree
  chart = "lepton"

  namespace = var.lepton_namespace

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "apiServer.name"
    value = var.lepton_api_server_name
  }

  set {
    name  = "web.name"
    value = var.lepton_web_name
  }

  set {
    name  = "web.enabled"
    value = var.lepton_web_enabled
  }

  set {
    name  = "apiServer.serviceAccountRoleArn"
    value = "arn:aws:iam::${local.account_id}:role/${aws_iam_role.s3-role.name}"
  }

  set {
    name  = "apiServer.bucketName"
    value = aws_s3_bucket.s3-bucket.bucket
  }

  set {
    name  = "apiServer.certificateArn"
    value = aws_acm_certificate.cert.arn
  }

  set {
    name  = "apiServer.rootDomain"
    value = aws_acm_certificate.cert.domain_name
  }

  set {
    name  = "apiServer.apiToken"
    value = var.api_token
  }

  depends_on = [
    module.eks,
    module.vpc,
    helm_release.aws_load_balancer_controller,
    aws_iam_role_policy_attachment.s3-role-policy-attachment
  ]
}
