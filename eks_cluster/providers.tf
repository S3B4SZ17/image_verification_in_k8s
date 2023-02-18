
terraform {
 backend "s3" {
   bucket         = "demo-eks-state-809870132669"
   key            = "terraform-state/demo-eks/terraform.tfstate"
   region         = "us-east-1"
   dynamodb_table = "terraform_mutex"
   encrypt        = true
   role_arn       = "arn:aws:iam::809870132669:role/github-tf-state-role"
 }
}

terraform {

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.47.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.4.3"
    }

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0.4"
    }

    cloudinit = {
      source  = "hashicorp/cloudinit"
      version = "~> 2.2.0"
    }
  }

  required_version = "~> 1.3"
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
  assume_role {
    role_arn     = format("arn:aws:iam::%s:role/%s", var.account_id, var.tf_foundation_role)
    session_name = "zaitch"
  }
}
