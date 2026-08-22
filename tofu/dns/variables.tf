# =============================================================================
# STOP -- READ BEFORE TOUCHING THIS MODULE (owner decision 2026-08-22, Infra backlog E7.T32)
#
# tofu/dns/ is a STUB. It has NEVER managed a DNS record: the state file holds
# zero resources (serial 1), and the module is this provider block plus two
# variables. There is no records.tf and nothing generates one.
#
# config/dns_records.csv is NOT applied to DNS by anything. NetworkService
# (src/homelab_gitops/domain/network.py) only appends rows to it and reads IPs
# back as an allocation ledger; scripts/technitium_manager.py convert-csv can
# render it to tofu JSON, but nothing runs that and nothing applies the result.
#
# Technitium serves 189 records today. The 127 records in infra.plexplease.com
# are owned by external-dns running with --policy=sync. COMPLETING THIS MODULE
# AND RUNNING `tofu apply` WOULD DELETE THOSE RECORDS: a provider that takes
# ownership of the zone reaps everything it does not declare, and external-dns
# would then fight it on every reconcile.
#
# Decision: LEAVE AS-IS. Neither build nor delete. Host DNS is hand-managed in
# Technitium. Do not "finish" this module.
# =============================================================================

variable "technitium_host" {
  type        = string
  description = "The URL of the Technitium DNS server (e.g., http://10.10.10.2:5380)"
}

variable "technitium_token" {
  type        = string
  description = "The API token for authentication"
  sensitive   = true
}
