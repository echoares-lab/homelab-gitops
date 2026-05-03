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

variable "host" {
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
  type = number
}

variable "vm_ram_gb" {
  type = number
}

variable "guest_id" {
  type = string
}

variable "library_name" {
  type = string
}

variable "template_name" {
  type = string
}

variable "vm_tags" {
  type = string
}

variable "disk_size_gb" {
  type    = number
  default = 50
}

variable "mac_address" {
  type    = string
  default = ""
}
