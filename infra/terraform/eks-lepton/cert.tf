resource "aws_acm_certificate" "cert" {
  domain_name               = "${module.eks.cluster_name}.cloud.lepton.ai"
  subject_alternative_names = ["*.${module.eks.cluster_name}.cloud.lepton.ai"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert-record" {
  allow_overwrite = true
  name            = tolist(aws_acm_certificate.cert.domain_validation_options)[0].resource_record_name
  records         = [tolist(aws_acm_certificate.cert.domain_validation_options)[0].resource_record_value]
  ttl             = 60
  type            = tolist(aws_acm_certificate.cert.domain_validation_options)[0].resource_record_type
  zone_id         = var.lepton_cloud_route53_zone_id
}
