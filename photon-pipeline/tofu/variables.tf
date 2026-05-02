variable "vcenter_server" {
  type = string
}

variable "vcenter_user" {
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

variable "vm_name" {
  type = string
}

variable "vm_cpu" {
  type    = number
  default = 2
}

variable "vm_ram_gb" {
  type    = number
  default = 8
}

variable "library_name" {
  type    = string
  default = "PHOTON"
}

variable "template_name" {
  type    = string
  default = "photon-5.0-minimal"
}

variable "vm_tags" {
  type    = list(string)
  default = ["photon"]
}

variable "disk_size_gb" {
  type    = number
  default = 50
}

variable "mac_address" {
  type    = string
  default = ""
}
