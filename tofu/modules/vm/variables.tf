variable "profile_name" {
  type        = string
  description = "Profile name"
}

variable "cpu" {
  type        = number
  description = "Number of CPUs"
  default     = 4
}

variable "memory" {
  type        = number
  description = "Memory in MB"
  default     = 8192
}

variable "disk" {
  type        = number
  description = "Disk size in GB"
  default     = 50
}

variable "datacenter" {
  type        = string
  description = "vCenter datacenter name"
}

variable "cluster" {
  type        = string
  description = "vCenter cluster name"
}

variable "datastore" {
  type        = string
  description = "vCenter datastore name"
}

variable "vcenter_server" {
  type        = string
  description = "vCenter server address"
  default     = ""
}

variable "vcenter_user" {
  type        = string
  description = "vCenter username"
  default     = ""
}

variable "vcenter_password" {
  type        = string
  description = "vCenter password"
  sensitive   = true
  default     = ""
}

variable "template_name" {
  type        = string
  description = "Template name for cloning"
  default     = ""
}

variable "network" {
  type        = string
  description = "Network name"
  default     = ""
}

variable "ipv4_address" {
  type        = string
  description = "Static IPv4 address"
  default     = ""
}

variable "ipv4_netmask" {
  type        = number
  description = "IPv4 netmask"
  default     = 24
}

variable "ipv4_gateway" {
  type        = string
  description = "IPv4 gateway"
  default     = ""
}

variable "dns_servers" {
  type        = list(string)
  description = "DNS servers"
  default     = ["8.8.8.8"]
}

variable "guest_id" {
  type        = string
  description = "Guest OS ID"
  default     = "ubuntu64Guest"
}

variable "library_name" {
  type        = string
  description = "Content library name"
  default     = ""
}

variable "mac_address" {
  type        = string
  description = "Static MAC address"
  default     = ""
}

variable "vm_tags" {
  type        = string
  description = "VM tags (comma-separated)"
  default     = ""
}

variable "host" {
  type        = string
  description = "vCenter host name"
  default     = ""
}
