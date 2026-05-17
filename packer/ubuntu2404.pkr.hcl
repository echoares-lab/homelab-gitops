packer {
  required_plugins {
    vsphere = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/vsphere"
    }
  }
}

variable "vcenter_server" {
  type = string
}

variable "vcenter_username" {
  type = string
}

variable "vcenter_password" {
  type      = string
  sensitive = true
}

variable "datacenter" {
  type = string
}

variable "cluster" {
  type = string
}

variable "datastore" {
  type = string
}

variable "network" {
  type = string
}

variable "ubuntu_iso_url" {
  type = string
}

variable "ubuntu_iso_checksum" {
  type = string
}

variable "ssh_username" {
  type = string
}

variable "ssh_password" {
  type      = string
  sensitive = true
}

source "vsphere-iso" "ubuntu2404" {
  vcenter_server      = var.vcenter_server
  username            = var.vcenter_username
  password            = var.vcenter_password
  insecure_connection = true

  datacenter = var.datacenter
  cluster    = var.cluster
  datastore  = var.datastore

  vm_name              = "ubuntu-24.04-golden-build"
  guest_os_type        = "ubuntu64Guest"
  firmware             = "bios"
  CPUs                 = 2
  RAM                  = 2048
  disk_controller_type = ["pvscsi"]
  storage {
    disk_size             = 20480
    disk_thin_provisioned = true
  }

  cdrom_type = "sata"

  network_adapters {
    network      = var.network
    network_card = "vmxnet3"
  }

  iso_url      = var.ubuntu_iso_url
  iso_checksum = var.ubuntu_iso_checksum

  http_directory = "${path.root}/http/ubuntu2404"
  http_port_min  = 8100
  http_port_max  = 8199

  boot_wait = "5s"
  boot_command = [
    "c<wait>",
    "linux /casper/vmlinuz autoinstall 'ds=nocloud-net;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/' ---<enter><wait3>",
    "initrd /casper/initrd<enter><wait3>",
    "boot<enter>"
  ]

  ssh_username = var.ssh_username
  ssh_password = var.ssh_password
  ssh_timeout  = "30m"

  convert_to_template = true

  content_library_destination {
    library = "GOLDEN"
    name    = "ubuntu-24.04-lts-golden"
    ovf     = true
    destroy = true
  }
}

build {
  sources = ["source.vsphere-iso.ubuntu2404"]

  provisioner "shell" {
    inline = [
      "echo 'Applying final updates...'",
      "sudo apt-get update -y",
      "sudo apt-get upgrade -y",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y open-vm-tools python3 tar rsync",
      "sudo apt-get autoremove -y",
      "sudo apt-get clean",
      "echo 'Build complete!'"
    ]
  }
}
