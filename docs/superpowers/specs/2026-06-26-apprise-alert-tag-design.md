# Apprise Alert Tag Delivery Design

## Problem

The Alertmanager webhook transformer posts notifications to Apprise without a
tag. The OpenBao-managed Apprise destination is intentionally tagged `alerts`,
so Apprise selects no notification service and returns HTTP 424.

## Design

Add `tag=alerts` to the form-encoded request sent by the Alertmanager webhook
transformer. Keep the OpenBao `APPRISE_CONFIG` tagging unchanged. The
transformer handles only Alertmanager traffic, so a fixed `alerts` tag is the
smallest configuration with a single clear behavior.

## Error Handling

Preserve the existing HTTP behavior: successful Apprise responses return 200
with the upstream status; upstream or request failures return 500 with the
captured error. This change only affects destination selection.

## Testing and Validation

Add a regression test that loads the transformer ConfigMap and verifies the
form payload includes `tag: alerts`. Run the targeted platform-readiness tests,
validate the GitOps manifests, deploy the ConfigMap through the existing GitOps
path, restart the transformer if reconciliation does not do so, and require a
synthetic Alertmanager webhook to return `apprise_status=204` (or another 2xx or
3xx Apprise status). Final acceptance requires confirmation that ntfy received
the synthetic alert.
