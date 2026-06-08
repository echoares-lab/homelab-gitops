terraform {
  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.0"
    }
  }
}

# VM provisioning module
# This module encapsulates vSphere VM provisioning logic
# In a real implementation, this would contain the full vsphere_virtual_machine resource
# and supporting data sources (datastore, network, template lookups, etc.)
#
# For now, this is a placeholder that demonstrates the modular structure.
# The root module (../main.tf) will call this module with profile-specific variables.
