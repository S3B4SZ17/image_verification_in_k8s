#!/bin/bash

# Setting up role for app-# IRSA configuration

ROLE_NAME="Readonly-ECR-$1" # the name of your IAM role
SERVICE_ACCOUNT_NAME="$1-sa" # the name of your service account name
SERVICE_ACCOUNT_NAMESPACE="$1" # the namespace for your service account
PROVIDER_ARN=$(terraform output -json | jq -r .oidc_provider_arn.value) # the ARN of your OIDC provider
ISSUER_HOSTPATH=$(aws eks describe-cluster --name demo-eks --query cluster.identity.oidc.issuer --output text | cut -f 3- -d'/') # the host path of your OIDC issuer

cat > assume-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "$PROVIDER_ARN"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
            "${ISSUER_HOSTPATH}:aud": "sts.amazonaws.com",
            "${ISSUER_HOSTPATH}:sub": "system:serviceaccount:${SERVICE_ACCOUNT_NAMESPACE}:${SERVICE_ACCOUNT_NAME}"
        }
      }
    }
  ]
}
EOF

aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://assume-policy.json
aws iam update-assume-role-policy --role-name $ROLE_NAME --policy-document file://assume-policy.json
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly