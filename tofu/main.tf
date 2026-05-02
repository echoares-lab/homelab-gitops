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

data "vsphere_datacenter" "dc" {
  name = var.datacenter
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.cluster
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_host" "host" {
  name          = var.host
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_datastore" "datastore" {
  name          = var.datastore
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_network" "network" {
  name          = var.network
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_content_library" "library" {
  name = var.library_name
}

data "vsphere_content_library_item" "template" {
  name       = var.template_name
  library_id = data.vsphere_content_library.library.id
  type       = "ovf"
}

data "vsphere_tag_category" "category" {
  name = "Provisioning"
}

data "vsphere_tag" "tags" {
  for_each    = toset(var.vm_tags)
  name        = each.value
  category_id = data.vsphere_tag_category.category.id
}

resource "vsphere_virtual_machine" "vm" {
  name             = var.vm_name
  resource_pool_id = data.vsphere_compute_cluster.cluster.resource_pool_id
  host_system_id   = data.vsphere_host.host.id
  datastore_id     = data.vsphere_datastore.datastore.id

  num_cpus = var.vm_cpu
  memory   = var.vm_ram_gb * 1024
  guest_id = "vmwarePhoton64Guest"

  network_interface {
    network_id   = data.vsphere_network.network.id
    use_static_mac = var.mac_address != "" ? true : false
    mac_address    = var.mac_address != "" ? var.mac_address : null
  }

  disk {
    label            = "disk0"
    size             = var.disk_size_gb
    thin_provisioned = true
  }

  clone {
    template_uuid = data.vsphere_content_library_item.template.id
  }

  tags = [for t in data.vsphere_tag.tags : t.id]

  lifecycle {
    ignore_changes = [
      clone[0].template_uuid,
    ]
  }
}

output "vm_ip" {
  value = vsphere_virtual_machine.vm.default_ip_address
}
