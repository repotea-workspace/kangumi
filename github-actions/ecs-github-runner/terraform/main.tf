
locals {

}

provider "alicloud" {
  access_key = var.ALI_ACCESS_KEY
  secret_key = var.ALI_SECRET_KEY
  region     = var.ALI_REGION
}

