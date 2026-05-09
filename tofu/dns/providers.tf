terraform {
  required_providers {
    technitium = {
      source  = "kenske/technitium"
      version = ">= 0.1.0"
    }
  }
}

provider "technitium" {
  host  = var.technitium_host
  token = var.technitium_token
}
