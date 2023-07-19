########################
# PROD ACCOUNT
# only open to platform/infra team
########################

###########################
# ADMIN - ALL WRITE ACCESS
###########################

resource "aws_iam_user" "prod_admins" {
  count = var.environment == "prod" ? length(var.admin_users) : 0

  name = var.admin_users[count.index]

  # keep the default "force_destroy = true"
  # since users can be recreated with the same name
  # and AWS IAM won't revoke anything so long as it's the same name
}

resource "aws_iam_group" "prod_admins" {
  count = (var.environment == "prod" && length(var.admin_users) > 0) ? 1 : 0

  name = "prod-admins"
  path = "/"

  lifecycle {
    precondition {
      condition     = lookup(var.account_ids, "prod", null) == "${data.aws_caller_identity.current.account_id}"
      error_message = "Specified environment does not match with the current STS session account ID"
    }
  }
}

resource "aws_iam_group_policy_attachment" "prod_admins" {
  count = (var.environment == "prod" && length(var.admin_users) > 0) ? 1 : 0

  group      = "prod-admins"
  policy_arn = "arn:${local.partition}:iam::aws:policy/AdministratorAccess"

  depends_on = [aws_iam_group.prod_admins]
}

resource "aws_iam_group_membership" "prod_admins" {
  count = (var.environment == "prod" && length(var.admin_users) > 0) ? 1 : 0

  name = "prod-admins"

  users = aws_iam_user.prod_admins.*.name
  group = "prod-admins"

  depends_on = [
    aws_iam_group_policy_attachment.prod_admins
  ]
}

#######################
# LIMITED WRITE ACCESS
#######################

resource "aws_iam_user" "prod_power_user" {
  count = var.environment == "prod" ? length(var.power_users) : 0

  name = var.power_users[count.index]

  # keep the default "force_destroy = true"
  # since users can be recreated with the same name
  # and AWS IAM won't revoke anything so long as it's the same name
}

resource "aws_iam_group" "prod_power_user" {
  count = (var.environment == "prod" && length(var.power_users) > 0) ? 1 : 0

  name = "prod-power-user"
  path = "/"

  lifecycle {
    precondition {
      condition     = lookup(var.account_ids, "prod", null) == "${data.aws_caller_identity.current.account_id}"
      error_message = "Specified environment does not match with the current STS session account ID"
    }
  }
}

resource "aws_iam_group_policy_attachment" "prod_power_user_billing" {
  count = (var.environment == "prod" && length(var.power_users) > 0) ? 1 : 0

  group      = "prod-power-user"
  policy_arn = "arn:${local.partition}:iam::aws:policy/AWSBillingReadOnlyAccess"

  depends_on = [aws_iam_group.prod_power_user]
}

resource "aws_iam_group_policy_attachment" "prod_power_user_iam_full_access" {
  count = (var.environment == "prod" && length(var.power_users) > 0) ? 1 : 0

  group      = "prod-power-user"
  policy_arn = "arn:${local.partition}:iam::aws:policy/IAMFullAccess"

  depends_on = [aws_iam_group.prod_power_user]
}

resource "aws_iam_group_policy_attachment" "prod_power_user_iam_change_password" {
  count = (var.environment == "prod" && length(var.power_users) > 0) ? 1 : 0

  group      = "prod-power-user"
  policy_arn = "arn:${local.partition}:iam::aws:policy/IAMUserChangePassword"

  depends_on = [aws_iam_group.prod_power_user]
}

resource "aws_iam_group_policy_attachment" "prod_power_user" {
  count = (var.environment == "prod" && length(var.power_users) > 0) ? 1 : 0

  group      = "prod-power-user"
  policy_arn = "arn:${local.partition}:iam::aws:policy/PowerUserAccess"

  depends_on = [aws_iam_group.prod_power_user]
}

resource "aws_iam_group_membership" "prod_power_user" {
  count = (var.environment == "prod" && length(var.power_users) > 0) ? 1 : 0

  name = "prod-power-user"

  users = aws_iam_user.prod_power_user.*.name
  group = "prod-power-user"

  depends_on = [
    aws_iam_group_policy_attachment.prod_power_user_billing,
    aws_iam_group_policy_attachment.prod_power_user_iam_full_access,
    aws_iam_group_policy_attachment.prod_power_user_iam_change_password,
    aws_iam_group_policy_attachment.prod_power_user
  ]
}

########################
# READ ONLY - NON ADMIN
########################

resource "aws_iam_user" "prod_read_only" {
  count = var.environment == "prod" ? length(var.read_only_users) : 0

  name = var.read_only_users[count.index]

  # TODO
  # force_destroy = false
}

resource "aws_iam_group" "prod_read_only" {
  count = (var.environment == "prod" && length(var.read_only_users) > 0) ? 1 : 0

  name = "prod-read-only"
  path = "/"

  lifecycle {
    precondition {
      condition     = lookup(var.account_ids, "prod", null) == "${data.aws_caller_identity.current.account_id}"
      error_message = "Specified environment does not match with the current STS session account ID"
    }
  }
}

resource "aws_iam_group_policy_attachment" "prod_read_only" {
  count = (var.environment == "prod" && length(var.read_only_users) > 0) ? 1 : 0

  group      = "prod-read-only"
  policy_arn = "arn:${local.partition}:iam::aws:policy/ReadOnlyAccess"

  depends_on = [aws_iam_group.prod_read_only]
}

resource "aws_iam_group_policy_attachment" "prod_read_only_iam_full_access" {
  count = (var.environment == "prod" && length(var.read_only_users) > 0) ? 1 : 0

  group      = "prod-read-only"
  policy_arn = "arn:${local.partition}:iam::aws:policy/IAMFullAccess"

  depends_on = [aws_iam_group.prod_read_only]
}

resource "aws_iam_group_policy_attachment" "prod_read_only_iam_change_password" {
  count = (var.environment == "prod" && length(var.read_only_users) > 0) ? 1 : 0

  group      = "prod-read-only"
  policy_arn = "arn:${local.partition}:iam::aws:policy/IAMUserChangePassword"

  depends_on = [aws_iam_group.prod_read_only]
}

resource "aws_iam_group_membership" "prod_read_only" {
  count = (var.environment == "prod" && length(var.read_only_users) > 0) ? 1 : 0

  name = "prod-read-only"

  users = aws_iam_user.prod_read_only.*.name
  group = "prod-read-only"

  depends_on = [
    aws_iam_group_policy_attachment.prod_read_only,
    aws_iam_group_policy_attachment.prod_read_only_iam_full_access,
    aws_iam_group_policy_attachment.prod_read_only_iam_change_password,
  ]
}
