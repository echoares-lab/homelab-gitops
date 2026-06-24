packer {
  required_plugins {
    vsphere = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/vsphere"
    }
  }
}

variable "profile_name" {
  type = string
}

variable "vm_name" {
  type = string
}

variable "name" {
  type = string
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

source "vsphere-iso" "fcos" {
  vcenter_server      = var.vcenter_server
  username            = var.vcenter_username
  password            = var.vcenter_password
  insecure_connection = true

  datacenter = var.datacenter
  cluster    = var.cluster
  datastore  = var.datastore

  vm_name              = "fcos-golden-build"
  guest_os_type        = "coreos64Guest"
  vm_version           = 21
  firmware             = "efi"
  CPUs                 = 2
  RAM                  = 2048
  disk_controller_type = ["pvscsi"]
  storage {
    disk_size             = 20480
    disk_thin_provisioned = true
  }

  network_adapters {
    network      = var.network
    network_card = "vmxnet3"
  }

  # Download the latest stable Fedora CoreOS Live ISO
  iso_url      = "https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/40.20240906.3.0/x86_64/fedora-coreos-40.20240906.3.0-live.x86_64.iso"
  iso_checksum = "sha256:5760135309cfcb2cb0ada13b65ac9b086ff85f485bb1a0ec72be1ee5033107d0"

  # Boot command for UEFI
  boot_wait      = "3s"
  http_directory = "${path.root}/../build/http/fcos"

  boot_command = [
    "e<down><down><end>",
    " coreos.inst.install_dev=/dev/sda",
    " coreos.inst.ignition_url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/installed.ign",
    " coreos.inst.platform_id=vmware",
    "<F10>"
  ]

  shutdown_command = "sudo systemctl poweroff"
  shutdown_timeout = "20m"

  communicator           = "ssh"
  ssh_username           = "core"
  ssh_private_key_file   = "~/.ssh/id_ed25519"
  ssh_timeout            = "20m"
  ssh_handshake_attempts = 100
  content_library_destination {
    library = "GOLDEN"
    name    = "fcos-latest-golden"
    ovf     = true
    destroy = true
  }
}

build {
  sources = ["source.vsphere-iso.fcos"]

  provisioner "shell" {
    inline = [
      "echo 'Fedora CoreOS installation complete and rebooted!'",
      "uname -a"
    ]
  }
}
