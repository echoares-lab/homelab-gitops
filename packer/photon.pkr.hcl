packer {
  required_plugins {
    vsphere = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/vsphere"
    }
  }
}

variable "vcenter_server" {
  type    = string
  default = "10.10.10.9"
}

variable "vcenter_username" {
  type    = string
  default = "administrator@vsphere.local"
}

variable "vcenter_password" {
  type      = string
  sensitive = true
}

variable "datacenter" {
  type    = string
  default = "HOMELAB"
}

variable "cluster" {
  type    = string
  default = "Primary"
}

variable "datastore" {
  type    = string
  default = "NVME_2TB_970_SAMSUNG_EVO_M.2"
}

variable "network" {
  type    = string
  default = "VM Network"
}

variable "photon_iso_url" {
  type    = string
  default = "https://packages.broadcom.com/photon/5.0/GA/iso/photon-minimal-5.0-dde71ec57.x86_64.iso"
}

variable "photon_iso_checksum" {
  type    = string
  default = "sha512:85cddaa8da26c095cf55d3f22f0838ad5d9ae73aa476d0c5c8e54bfbfcb432deaf940733c2cb5af14d1e5b133da65c17f3f4e215bf381d5b8b411d548b66a463"
}

variable "ssh_username" {
  type    = string
  default = "ansible"
}

variable "ssh_password" {
  type      = string
  sensitive = true
  default   = "Singer4life!@"
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

  ssh_username = var.ssh_username
  ssh_password = var.ssh_password
  ssh_timeout  = "20m"

  convert_to_template = true
  
  content_library_destination {
    library = "PHOTON"
    name    = "photon-5.0-minimal-golden"
    ovf     = true
    destroy = true
  }
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
