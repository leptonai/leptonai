data "aws_iam_policy_document" "satellite" {
  statement {
    sid     = ""
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.satellite_node_user_arn]
    }
  }
}

# IAM ROLES ANYWHERE can only be used for short-term credentials
# thus easier to use assume-role with user credentials
# and reauthenticate every ~12-hour (max_session_duration)
resource "aws_iam_role" "satellite" {
  name = "${var.cluster_name}-satellite-${var.satellite_name}"

  assume_role_policy = data.aws_iam_policy_document.satellite.json

  # force detaching policies from this role
  # to speed up uninstall process
  force_detach_policies = true

  # 12-hour
  max_session_duration = 43200
}

resource "aws_iam_role_policy_attachment" "satellite_AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "${local.iam_role_policy_prefix}/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.satellite.name
}

resource "aws_iam_role_policy_attachment" "satellite_AmazonS3ReadOnlyAccess" {
  policy_arn = "${local.iam_role_policy_prefix}/AmazonS3ReadOnlyAccess"
  role       = aws_iam_role.satellite.name
}
