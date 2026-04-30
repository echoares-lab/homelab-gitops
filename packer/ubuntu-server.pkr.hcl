packer {
  required_plugins {
    vsphere = {
      version = ">= 1.2.0"
      source  = "github.com/hashicorp/vsphere"
    }
  }
}

# Variable declarations mapping to ENV vars
variable "vcenter_server"           { type = string; default = env("VCENTER_SERVER") }
variable "vcenter_user"             { type = string; default = env("VCENTER_USERNAME") }
variable "vcenter_password"         { type = string; default = env("VCENTER_PASSWORD"); sensitive = true }
variable "datacenter"               { type = string; default = env("VCENTER_DATACENTER") }
variable "datastore"                { type = string; default = env("VCENTER_DATASTORE") }
variable "cluster"                  { type = string; default = env("VCENTER_CLUSTER") }
variable "network"                  { type = string; default = env("VCENTER_NETWORK") }
variable "vm_name"                  { type = string; default = env("PACKER_VM_NAME") }
variable "cpu_count"                { type = number; default = env("TEMPLATE_CPU_COUNT") }
variable "memory_mb"                { type = number; default = env("TEMPLATE_MEMORY_MB") }
variable "disk_size_mb"             { type = number; default = env("TEMPLATE_DISK_SIZE_MB") }
variable "ssh_username"             { type = string; default = env("PACKER_SSH_USERNAME") }
variable "ssh_public_key"           { type = string; default = env("SSH_ADMIN_SSH_PUBKEY") }
variable "iso_url"                  { type = string; default = env("UBUNTU_ISO_URL") }
variable "iso_checksum"             { type = string; default = env("UBUNTU_ISO_CHECKSUM") }
variable "folder"                   { type = string; default = env("VCENTER_BUILD_FOLDER") }

source "vsphere-iso" "ubuntu" {
  vcenter_server      = var.vcenter_server
  username            = var.vcenter_user
  password            = var.vcenter_password
  insecure_connection = true

  vm_name              = var.vm_name
  guest_os_type        = "ubuntu64Guest"
  folder               = var.folder
  
  cluster              = var.cluster
  datacenter           = var.datacenter
  datastore            = var.datastore
  
  CPUs                 = var.cpu_count
  RAM                  = var.memory_mb
  RAM_reserve_all      = true
  
  disk_controller_type = ["pvscsi"]
  storage {
    disk_size             = var.disk_size_mb
    disk_thin_provisioned = true
  }
  
  network_adapters {
    network      = var.network
    network_card = "vmxnet3"
  }
  
  iso_url      = var.iso_url
  iso_checksum = var.iso_checksum

  boot_command = [
    "<wait>e<wait>",
    "<down><down><down><end>",
    " autoinstall ds=nocloud-net;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/",
    "<f10>"
  ]

  http_content = {
    "/user-data" = templatefile("user-data.pkrtpl.hcl", {
      ssh_public_key = var.ssh_public_key
      ssh_username   = var.ssh_username
    })
    "/meta-data" = ""
  }

  ssh_username = var.ssh_username
  ssh_timeout  = "30m"

  convert_to_template = true
}

build {
  sources = ["source.vsphere-iso.ubuntu"]

  provisioner "ansible" {
    playbook_file = "../ansible/packer_provision.yml"
    user          = var.ssh_username
    use_proxy     = false
    extra_arguments = [
      "--extra-vars", "ansible_user=${var.ssh_username}"
    ]
  }
}
