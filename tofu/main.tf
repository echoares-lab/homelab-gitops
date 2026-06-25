terraform {
  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = ">= 2.0.0"
    }
  }
}

provider "vsphere" {
  user                 = var.vcenter_user
  password             = var.vcenter_password
  vsphere_server       = var.vcenter_server
  allow_unverified_ssl = true
}

# Call the VM module for provisioning
module "vm" {
  source = "./modules/vm"

  profile_name     = var.profile_name
  vm_name          = var.vm_name
  cpu              = var.vm_cpu
  memory           = var.vm_ram_gb * 1024
  disk             = var.disk_size_gb
  datacenter       = var.datacenter
  cluster          = var.cluster
  datastore        = var.datastore
  vcenter_server   = var.vcenter_server
  vcenter_user     = var.vcenter_user
  vcenter_password = var.vcenter_password
  template_name    = var.template_name
  network          = var.network
  ipv4_address     = var.ipv4_address
  ipv4_netmask     = var.ipv4_netmask
  ipv4_gateway     = var.ipv4_gateway
  dns_servers      = var.dns_servers
  guest_id         = var.guest_id
  library_name     = var.library_name
  mac_address      = var.mac_address
  vm_tags          = var.vm_tags
  host             = var.host
  firmware         = var.firmware

}

output "vm_ip" {
  value       = module.vm.vm_ip
  description = "VM IP address"
}

output "vm_id" {
  value       = module.vm.vm_id
  description = "VM identifier"
}
