#!/bin/sh
set -eu

: "${GOVC_URL:?GOVC_URL must identify vCenter}"
: "${GOVC_USERNAME:?GOVC_USERNAME is required}"
: "${GOVC_PASSWORD:?GOVC_PASSWORD is required}"
export GOVC_URL GOVC_USERNAME GOVC_PASSWORD

HOST=10.10.10.13
VM=/HOMELAB/vm/k3s-deadman-01.infra.plexplease.com
govc host.autostart.configure -host "$HOST" -enabled=true -start-delay 30
govc host.autostart.add -host "$HOST" -start-action powerOn -start-delay 30 -start-order 1 "$VM"
