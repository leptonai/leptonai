resource "aws_s3_bucket" "s3-bucket" {
  bucket        = "s3-lepton-${var.cell_name}"
  force_destroy = true
}

# TODO: finer grain tuning for s3 policies: for example, we should not allow
# LeptonDeployment to have write permissions
resource "aws_iam_policy" "s3-policy" {
  name = "s3-policy-${var.cell_name}"
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
  description = "S3 IAM policy"

  depends_on = [
    aws_s3_bucket.s3-bucket
  ]
}
