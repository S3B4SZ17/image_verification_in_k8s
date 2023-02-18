data "aws_availability_zones" "available" {}

locals {
  cluster_name = "${var.cluster_name}"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "3.19.0"

  name = var.vpc_name

  cidr = var.cidr
  azs  = slice(data.aws_availability_zones.available.names, 0, 3)

  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                      = 1
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"             = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.5.1"

  cluster_name    = local.cluster_name
  cluster_version = "1.24"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true
  enable_irsa                    = true

  eks_managed_node_group_defaults = {
    ami_type = var.ami_type

  }

  eks_managed_node_groups = {
    one = {
      name = var.node_groups[0]

      instance_types = ["t3.small"]

      min_size     = var.min_size
      max_size     = var.max_size
      desired_size = var.desired_size
    }

    two = {
      name = var.node_groups[1]

      instance_types = ["t3.small"]

      min_size     = var.min_size
      max_size     = var.max_size
      desired_size = var.desired_size
    }
  }
}

# key rotation is only supported for ENCRYPT_DECRYPT
resource "aws_kms_key" "cosign_signing_key" {
  description              = "KMS key for signing images"
  key_usage                = "SIGN_VERIFY"
  deletion_window_in_days  = 30
  enable_key_rotation      = false
  customer_master_key_spec = "RSA_4096"
}
resource "aws_kms_alias" "cosign_signing_key_alias" {
  name          = "alias/cosign-key"
  target_key_id = aws_kms_key.cosign_signing_key.key_id
}
