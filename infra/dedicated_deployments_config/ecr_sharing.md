## ECR Cross Account Access

For more detailed instructions, please refer to https://repost.aws/knowledge-center/secondary-account-access-ecr.

1. Create a registry replication rule if the customer account's cluster is not in `us-east-1`.

2. Create a repository permission rule to allow ECR access. Note that this is a per-repository setting (need to click the repository botton on the AWS console). We need to grant permissions to:

   - Lepton API Server
   - Lepton Operator
   - Lepton

3. Here is an example permission JSON:

```json
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowPullFromPromptAI",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::<account_id>:root"
        },
        "Action": [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
}
```

Please note that in this configuration, we delegate permission to the root user of the customer account. In the future, we may grant this to a defined role or IAM user.