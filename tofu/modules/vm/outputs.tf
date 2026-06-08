output "vm_id" {
  value       = "vm-${var.profile_name}"
  description = "VM identifier"
}

output "vm_ip" {
  value       = var.ipv4_address != "" ? var.ipv4_address : "10.10.10.50"
  description = "VM IP address"
}

output "vm_name" {
  value       = var.profile_name
  description = "VM name"
}
