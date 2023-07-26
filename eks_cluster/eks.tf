
module "eks-cluster" {

  source              = "git::https://github.com/S3B4SZ17/tf-modules.git//eks-cluster?ref=main"
  
  region              = var.region
  cluster_name        = var.cluster_name
  account_id          = var.account_id
  tf_foundation_role  = var.tf_foundation_role
  tf_state_role       = var.tf_state_role

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
