# later sources taking precedence over earlier ones
# so the variables in this file may be overwritten by -var flags
# see https://developer.hashicorp.com/terraform/language/values/variables#variable-definition-precedence for ordering
#
# default values are defined in "tfvars" files
# optionally, overwrite those in the following flags/env vars

deployment_environment    = "PROD"
auth_users_iam_group_name = "prod-admins"
region                    = "us-west-2"

lepton_cloud_route53_zone_id = "Z0305788EACPTSFEJARC"
root_hostname                = "app.lepton.ai"
tls_cert_arn_id              = "6767482b-dfe1-4802-afe4-408df40a264a"

shared_alb_route53_zone_id = "Z08261432QC9RN8752CXF"
shared_alb_root_hostname   = "edr.lepton.ai"

aurora_master_username = "root"

# TODO: change to prod channel
# ref. https://grafana.com/blog/2020/02/25/step-by-step-guide-to-setting-up-prometheus-alertmanager-with-slack-pagerduty-and-gmail/
alertmanager_slack_channel     = "#alertmanager-test"
alertmanager_slack_webhook_url = "https://hooks.slack.com/services/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"
alertmanager_target_namespaces = ".*"
