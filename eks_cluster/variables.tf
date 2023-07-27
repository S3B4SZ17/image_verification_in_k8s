variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the cluster"
  type        = string
  default     = "demo-eks"
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
  default     = "809870132669"
}

variable "tf_foundation_role" {
  description = "IAM role for deploying with Terraform"
  type        = string
  default     = "github-tf-foundational-deploy-role"
}

variable "tf_state_role" {
  description = "IAM role for storing the Terraform state files in S3 buckets"
  type        = string
  default     = "github-tf-state-role"
}

variable "vpc_name" {
  description = "Name of the vpc"
  type        = string
  default     = "demo-eks_vpc"
}
