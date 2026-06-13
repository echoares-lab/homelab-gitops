output "vm_id" {
  value       = vsphere_virtual_machine.vm.id
  description = "VM identifier"
}

output "vm_ip" {
  value       = vsphere_virtual_machine.vm.default_ip_address
  description = "VM IP address"
}

output "vm_name" {
  value       = vsphere_virtual_machine.vm.name
  description = "VM name"
}
