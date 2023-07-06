########################
# DEV ACCOUNT
# open to everyone
########################

###########################
# ADMIN - ALL WRITE ACCESS
###########################

resource "aws_iam_user" "dev_admins" {
  count = var.environment == "dev" ? length(var.admin_users) : 0

  name = var.admin_users[count.index]

  # keep the default "force_destroy = true"
  # since users can be recreated with the same name
  # and AWS IAM won't revoke anything so long as it's the same name
}

resource "aws_iam_group" "dev_admins" {
  count = (var.environment == "dev" && length(var.admin_users) > 0) ? 1 : 0

  name = "dev-admins"
  path = "/"

  lifecycle {
    precondition {
      condition     = lookup(var.account_ids, "dev", null) == "${data.aws_caller_identity.current.account_id}"
      error_message = "Specified environment does not match with the current STS session account ID"
    }
  }
}

resource "aws_iam_group_policy_attachment" "dev_admins" {
  count = (var.environment == "dev" && length(var.admin_users) > 0) ? 1 : 0

  group      = "dev-admins"
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

  depends_on = [aws_iam_group.dev_admins]
}

resource "aws_iam_group_membership" "dev_admins" {
  count = (var.environment == "dev" && length(var.admin_users) > 0) ? 1 : 0

  name = "dev-admins"

  users = aws_iam_user.dev_admins.*.name
  group = "dev-admins"

  depends_on = [
    aws_iam_group_policy_attachment.dev_admins
  ]
}

#####################################
# POWER USER - LIMITED WRITE ACCESS
#####################################

resource "aws_iam_user" "dev_power_user" {
  count = var.environment == "dev" ? length(var.power_users) : 0

  name = var.power_users[count.index]

  # keep the default "force_destroy = true"
  # since users can be recreated with the same name
  # and AWS IAM won't revoke anything so long as it's the same name
}

resource "aws_iam_group" "dev_power_user" {
  count = (var.environment == "dev" && length(var.power_users) > 0) ? 1 : 0

  name = "dev-power-user"
  path = "/"

  lifecycle {
    precondition {
      condition     = lookup(var.account_ids, "dev", null) == "${data.aws_caller_identity.current.account_id}"
      error_message = "Specified environment does not match with the current STS session account ID"
    }
  }
}

resource "aws_iam_group_policy_attachment" "dev_power_user_billing" {
  count = (var.environment == "dev" && length(var.power_users) > 0) ? 1 : 0

  group      = "dev-power-user"
  policy_arn = "arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess"

  depends_on = [aws_iam_group.dev_power_user]
}

resource "aws_iam_group_policy_attachment" "dev_power_user_iam_full_access" {
  count = (var.environment == "dev" && length(var.power_users) > 0) ? 1 : 0

  group      = "dev-power-user"
  policy_arn = "arn:aws:iam::aws:policy/IAMFullAccess"

  depends_on = [aws_iam_group.dev_power_user]
}

resource "aws_iam_group_policy_attachment" "dev_power_user_iam_change_password" {
  count = (var.environment == "dev" && length(var.power_users) > 0) ? 1 : 0

  group      = "dev-power-user"
  policy_arn = "arn:aws:iam::aws:policy/IAMUserChangePassword"

  depends_on = [aws_iam_group.dev_power_user]
}

resource "aws_iam_group_policy_attachment" "dev_power_user" {
  count = (var.environment == "dev" && length(var.power_users) > 0) ? 1 : 0

  group      = "dev-power-user"
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"

  depends_on = [aws_iam_group.dev_power_user]
}

resource "aws_iam_group_membership" "dev_power_user" {
  count = (var.environment == "dev" && length(var.power_users) > 0) ? 1 : 0

  name = "dev-power-user"

  users = aws_iam_user.dev_power_user.*.name
  group = "dev-power-user"

  depends_on = [
    aws_iam_group_policy_attachment.dev_power_user_billing,
    aws_iam_group_policy_attachment.dev_power_user_iam_full_access,
    aws_iam_group_policy_attachment.dev_power_user_iam_change_password,
    aws_iam_group_policy_attachment.dev_power_user
  ]
}

########################
# READ ONLY - NON ADMIN
########################

resource "aws_iam_user" "dev_read_only" {
  count = var.environment == "dev" ? length(var.read_only_users) : 0

  name = var.read_only_users[count.index]

  # keep the default "force_destroy = true"
  # since users can be recreated with the same name
  # and AWS IAM won't revoke anything so long as it's the same name
}

resource "aws_iam_group" "dev_read_only" {
  count = (var.environment == "dev" && length(var.read_only_users) > 0) ? 1 : 0

  name = "dev-read-only"
  path = "/"

  lifecycle {
    precondition {
      condition     = lookup(var.account_ids, "dev", null) == "${data.aws_caller_identity.current.account_id}"
      error_message = "Specified environment does not match with the current STS session account ID"
    }
  }
}

resource "aws_iam_group_policy_attachment" "dev_read_only" {
  count = (var.environment == "dev" && length(var.read_only_users) > 0) ? 1 : 0

  group      = "dev-read-only"
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"

  depends_on = [aws_iam_group.dev_read_only]
}

resource "aws_iam_group_policy_attachment" "dev_read_only_iam_full_access" {
  count = (var.environment == "dev" && length(var.read_only_users) > 0) ? 1 : 0

  group      = "dev-read-only"
  policy_arn = "arn:aws:iam::aws:policy/IAMFullAccess"

  depends_on = [aws_iam_group.dev_read_only]
}

resource "aws_iam_group_policy_attachment" "dev_read_only_iam_change_password" {
  count = (var.environment == "dev" && length(var.read_only_users) > 0) ? 1 : 0

  group      = "dev-read-only"
  policy_arn = "arn:aws:iam::aws:policy/IAMUserChangePassword"

  depends_on = [aws_iam_group.dev_read_only]
}

resource "aws_iam_group_membership" "dev_read_only" {
  count = (var.environment == "dev" && length(var.read_only_users) > 0) ? 1 : 0

  name = "dev-read-only"

  users = aws_iam_user.dev_read_only.*.name
  group = "dev-read-only"

  depends_on = [
    aws_iam_group_policy_attachment.dev_read_only,
    aws_iam_group_policy_attachment.dev_read_only_iam_full_access,
    aws_iam_group_policy_attachment.dev_read_only_iam_change_password
  ]
}
