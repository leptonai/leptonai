resource "aws_s3_bucket" "s3-bucket" {
  bucket = "s3-lepton-${local.cluster_name}"

  tags = {
    Name        = "s3-lepton-${local.cluster_name}"
    Environment = "Dev"
  }
}

# TODO: finer grain tuning for s3 policies: for example, we should not allow
# LeptonDeployment to have write permissions
resource "aws_iam_policy" "s3-policy" {
  name = "s3-policy-${local.cluster_name}"
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Action : [
          "s3:ListBucket",
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:GetBucketLocation"
        ],
        Resource : [
          "arn:aws:s3:::${aws_s3_bucket.s3-bucket.bucket}",
          "arn:aws:s3:::${aws_s3_bucket.s3-bucket.bucket}/*"
        ]
      }
    ]
  })
  description = "ALB IAM policy"

  depends_on = [
    aws_s3_bucket.s3-bucket
  ]
}

resource "aws_iam_role" "s3-role" {
  name = "s3-role-${local.cluster_name}"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Principal : {
          Federated : "arn:aws:iam::${local.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}"
        },
        Action : "sts:AssumeRoleWithWebIdentity",
        Condition : {
          StringEquals : {
            "oidc.eks.${var.region}.amazonaws.com/id/${local.oidc_id}:aud" : "sts.amazonaws.com",
          }
        }
      }
    ]
  })

  depends_on = [
    aws_s3_bucket.s3-bucket
  ]
}

resource "aws_iam_role_policy_attachment" "s3-role-policy-attachment" {
  policy_arn = "arn:aws:iam::${local.account_id}:policy/${aws_iam_policy.s3-policy.name}"
  role       = aws_iam_role.s3-role.name

  depends_on = [
    aws_iam_policy.s3-policy,
    aws_iam_role.s3-role
  ]
}
