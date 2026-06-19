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

variable "photon_iso_url" {
  type = string
}

variable "photon_iso_checksum" {
  type = string
}

variable "ssh_username" {
  type = string
}

variable "ssh_password" {
  type      = string
  sensitive = true
}

source "vsphere-iso" "photon" {
  vcenter_server      = var.vcenter_server
  username            = var.vcenter_username
  password            = var.vcenter_password
  insecure_connection = true

  datacenter = var.datacenter
  cluster    = var.cluster
  datastore  = var.datastore

  vm_name              = "photon-5.0-golden-build"
  guest_os_type        = "vmwarePhoton64Guest"
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

  iso_url      = var.photon_iso_url
  iso_checksum = var.photon_iso_checksum

  # Attach Kickstart via secondary CD-ROM
  cd_files = ["http/ks.json"]
  
  boot_wait = "5s"
  boot_command = [
    "<esc><wait5s>",
    "vmlinuz initrd=initrd.img root=/dev/ram0 ks=cdrom:/ks.json photon.media=cdrom<enter>"
  ]

  ssh_username           = var.ssh_username
  ssh_password           = var.ssh_password
  ssh_timeout            = "20m"
  pause_before_connecting = "10s"

  convert_to_template = true
}

build {
  sources = ["source.vsphere-iso.photon"]

  provisioner "shell" {
    inline = [
      "echo 'Applying final updates...'",
      "tdnf update -y",
      "tdnf install -y sudo python3 tar rsync",
      "echo 'Build complete!'"
    ]
  }
}
