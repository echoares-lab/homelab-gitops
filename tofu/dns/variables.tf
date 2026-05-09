variable "technitium_host" {
  type        = string
  description = "The URL of the Technitium DNS server (e.g., http://10.10.10.2:5380)"
}

variable "technitium_token" {
  type        = string
  description = "The API token for authentication"
  sensitive   = true
}
