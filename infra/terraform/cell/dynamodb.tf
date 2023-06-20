resource "aws_dynamodb_table" "tuna" {
  name         = "lepton-db-${var.cell_name}-tuna"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "Key"

  attribute {
    name = "Key"
    type = "S"
  }
}

resource "aws_iam_policy" "dynamodb-policy" {
  name = "dynamodb-policy-${var.cell_name}-tuna"
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DescribeTable"
        ],
        "Resource" : [
          "arn:aws:dynamodb:*:*:table/${aws_dynamodb_table.tuna.name}"
        ]
      }
    ]
  })
  description = "DynamoDB IAM policy for tuna"

  depends_on = [
    aws_dynamodb_table.tuna
  ]
}
