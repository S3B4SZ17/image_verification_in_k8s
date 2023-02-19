#!/bin/bash

# Setting up role for app-# IRSA configuration

ROLE_NAME="Push-ECR-$1" # the name of your IAM role

cat > push-ecr-assume-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::809870132669:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:sub": "repo:S3B4SZ17/pong-app:*",
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

cat > push-ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:CompleteLayerUpload",
                "ecr:GetAuthorizationToken",
                "ecr:UploadLayerPart",
                "ecr:InitiateLayerUpload",
                "ecr:BatchCheckLayerAvailability",
                "ecr:PutImage"
            ],
            "Resource": "*"
        }
    ]
}
EOF

cat > kms-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey",
                "kms:Encrypt",
                "kms:GenerateDataKey*",
                "kms:ReEncrypt*",
                "kms:GetPublicKey",
                "kms:ReEncrypt*",
                "kms:Sign",
                "kms:Verify"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://push-ecr-assume-policy.json
aws iam put-role-policy --role-name $ROLE_NAME --policy-name Push-ECR --policy-document file://push-ecr-policy.json
aws iam put-role-policy --role-name $ROLE_NAME --policy-name KMS-cosign --policy-document file://kms-policy.json
