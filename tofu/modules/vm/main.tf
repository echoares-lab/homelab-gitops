terraform {
  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.0"
    }
  }
}

data "vsphere_datacenter" "dc" {
  name = var.datacenter
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.cluster
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

data "vsphere_virtual_machine" "template" {
  name          = var.template_name
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_host" "host" {
  count         = var.host != "" ? 1 : 0
  name          = var.host
  datacenter_id = data.vsphere_datacenter.dc.id
}

resource "vsphere_virtual_machine" "vm" {
  name             = var.vm_name
  resource_pool_id = data.vsphere_compute_cluster.cluster.resource_pool_id
  datastore_id     = data.vsphere_datastore.datastore.id
  host_system_id   = var.host != "" ? data.vsphere_host.host[0].id : null

  wait_for_guest_net_timeout = 0

  num_cpus         = var.cpu
  memory           = var.memory
  guest_id         = var.guest_id
  firmware         = var.firmware
  hardware_version = 21

  scsi_type = "pvscsi"

  network_interface {
    network_id   = data.vsphere_network.network.id
    adapter_type = "vmxnet3"
    mac_address  = var.mac_address != "" ? var.mac_address : null
  }

  disk {
    label            = "disk0"
    size             = var.disk
    thin_provisioned = true
  }

  cdrom {
    client_device = true
  }

  extra_config = var.ignition_data != null ? {
    "guestinfo.ignition.config.data"          = base64encode(var.ignition_data)
    "guestinfo.ignition.config.data.encoding" = "base64"
  } : null

  clone {
    template_uuid = data.vsphere_virtual_machine.template.id

    dynamic "customize" {
      for_each = var.os_type != "fcos" && var.ipv4_address != "" ? [1] : []
      content {
        linux_options {
          host_name = split(".", var.vm_name)[0]
          domain    = length(split(".", var.vm_name)) > 1 ? join(".", slice(split(".", var.vm_name), 1, length(split(".", var.vm_name)))) : "local"
        }
        network_interface {
          ipv4_address = var.ipv4_address
          ipv4_netmask = var.ipv4_netmask
        }
        ipv4_gateway    = var.ipv4_gateway
        dns_server_list = var.dns_servers
      }
    }
  }

  lifecycle {
    ignore_changes = [
      clone[0].template_uuid,
    ]
  }
}
