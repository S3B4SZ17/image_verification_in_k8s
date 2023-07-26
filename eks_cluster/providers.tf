
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
