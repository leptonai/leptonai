resource "aws_s3_bucket" "s3-bucket" {
  bucket        = "s3-lepton-${var.workspace_name}"
  force_destroy = true
}

resource "aws_iam_policy" "s3-policy" {
  name = "s3-policy-${var.workspace_name}"
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
          "arn:${local.partition}:s3:::${aws_s3_bucket.s3-bucket.bucket}",
          "arn:${local.partition}:s3:::${aws_s3_bucket.s3-bucket.bucket}/*"
        ]
      }
    ]
  })
  description = "S3 IAM policy"

  depends_on = [
    aws_s3_bucket.s3-bucket
  ]
}

resource "aws_iam_policy" "s3-ro-policy" {
  name = "s3-ro-policy-${var.workspace_name}"
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect : "Allow",
        Action : [
          "s3:GetObject",
        ],
        Resource : [
          "arn:${local.partition}:s3:::${aws_s3_bucket.s3-bucket.bucket}/*"
        ]
      }
    ]
  })
  description = "S3 IAM policy"

  depends_on = [
    aws_s3_bucket.s3-bucket
  ]
}
