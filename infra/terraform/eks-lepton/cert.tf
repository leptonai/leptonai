resource "aws_acm_certificate" "cert" {
  domain_name               = var.shared_alb_main_domain
  subject_alternative_names = ["*.${var.shared_alb_main_domain}"]
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
  zone_id         = var.shared_alb_route53_zone_id
}
