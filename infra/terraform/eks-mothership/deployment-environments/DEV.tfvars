# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment    = "DEV"
auth_users_iam_group_name = "dev"
region                    = "us-east-1"

lepton_cloud_route53_zone_id = "Z007822916VK7B4DFVMP7"
root_hostname                = "cloud.lepton.ai"
tls_cert_arn_id              = "d8d5e0e1-ecc5-4716-aa79-01625e60704d"

shared_alb_route53_zone_id = "Z07918881RBIVGJY04WCJ"
shared_alb_root_hostname   = "dev.lepton.ai"

aurora_master_username = "root"

# ref. https://grafana.com/blog/2020/02/25/step-by-step-guide-to-setting-up-prometheus-alertmanager-with-slack-pagerduty-and-gmail/
alertmanager_slack_channel     = "#alertmanager-test"
alertmanager_slack_webhook_url = "https://hooks.slack.com/services/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"
alertmanager_target_namespaces = ".*"
