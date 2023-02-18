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

variable "vpc_name" {
  description = "Name of the vpc"
  type        = string
  default     = "personal_vpc"
}

variable "cidr" {
  description = "cidr"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnets"
  type        = list(string)
  default     = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]
}

variable "ami_type" {
  description = "AMI type"
  type        = string
  default     = "AL2_x86_64"
}

variable "node_groups" {
  description = "Names of the node groups"
  type        = list(string)
  default     = ["node-group-1", "node-group-2"]
}

variable "min_size" {
  description = "AMI type"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "AMI type"
  type        = number
  default     = 1
}

variable "desired_size" {
  description = "AMI type"
  type        = number
  default     = 1
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
