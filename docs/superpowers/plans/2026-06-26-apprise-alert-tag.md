# Apprise Alert Tag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure Alertmanager webhook notifications select the OpenBao-configured Apprise destination tagged `alerts`.

**Architecture:** Keep the tagged Apprise destination unchanged and add `tag=alerts` to the transformer's form-encoded request. Protect the behavior with a manifest-level regression test, then validate locally and through the live cluster path.

**Tech Stack:** Kubernetes ConfigMap YAML, embedded Python 3, pytest, PyYAML, External Secrets, Apprise API

## Global Constraints

- Preserve the existing transformer response and error behavior.
- Do not expose the OpenBao APPRISE_CONFIG value or ntfy topic.
- Keep the change limited to issue #117.

---

### Task 1: Send the Apprise alert tag

**Files:**
- Modify: `tests/test_k3s_platform_readiness.py`
- Modify: `kubernetes/platform/apprise/overlays/k3s-01/alertmanager-webhook-config.yaml`

**Interfaces:**
- Consumes: the ConfigMap `data.server.py` embedded transformer source.
- Produces: an Apprise form payload containing `title`, `body`, `type`, and `tag=alerts`.

- [ ] **Step 1: Write the failing regression test**

```python
def test_alertmanager_webhook_targets_apprise_alerts_tag() -> None:
    document = load_yaml_documents(
        PLATFORM_ROOT
        / "apprise"
        / "overlays"
        / "k3s-01"
        / "alertmanager-webhook-config.yaml"
    )[0]

    server_source = document["data"]["server.py"]

    assert '"tag": "alerts"' in server_source
```

- [ ] **Step 2: Run the test and verify RED**

Run: `pytest -q tests/test_k3s_platform_readiness.py::test_alertmanager_webhook_targets_apprise_alerts_tag`

Expected: FAIL because `server.py` does not contain `"tag": "alerts"`.

- [ ] **Step 3: Add the minimal transformer behavior**

Change the form payload in `alertmanager-webhook-config.yaml` to:

```python
data = urllib.parse.urlencode(
    {
        "title": title,
        "body": body,
        "type": notify_type,
        "tag": "alerts",
    }
).encode()
```

- [ ] **Step 4: Run targeted and manifest validation**

Run:

```bash
pytest -q tests/test_k3s_platform_readiness.py
python3 scripts/validate_gitops_manifests.py
```

Expected: all tests pass and manifest validation reports success.

- [ ] **Step 5: Commit the implementation**

```bash
git add tests/test_k3s_platform_readiness.py kubernetes/platform/apprise/overlays/k3s-01/alertmanager-webhook-config.yaml
git commit -m "fix(apprise): target alerts-tagged destination"
```

### Task 2: Verify live end-to-end delivery

**Files:**
- No repository files modified.

**Interfaces:**
- Consumes: reconciled ConfigMap, restarted transformer pod, and existing Apprise Secret.
- Produces: successful synthetic webhook response and ntfy receipt confirmation.

- [ ] **Step 1: Apply the updated ConfigMap and restart the transformer**

Run:

```bash
ssh core@10.10.10.50 \
  'sudo kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml apply -f -' \
  < kubernetes/platform/apprise/overlays/k3s-01/alertmanager-webhook-config.yaml
ssh core@10.10.10.50 \
  'sudo kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml -n notifications rollout restart deployment/apprise-alertmanager-webhook && sudo kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml -n notifications rollout status deployment/apprise-alertmanager-webhook --timeout=180s'
```

- [ ] **Step 2: Send the synthetic Alertmanager payload**

Execute a Python `urllib.request` POST inside
`deployment/apprise-alertmanager-webhook` using the RUNBOOK payload:

```json
{"status":"firing","alerts":[{"status":"firing","labels":{"alertname":"SyntheticTest","severity":"info"},"annotations":{"summary":"Apprise ntfy path test after issue 117 fix"}}]}
```

Expected: webhook HTTP 200 with `apprise_status=204` or another 2xx/3xx upstream status.

- [ ] **Step 3: Check component logs**

Inspect transformer and Apprise logs since the rollout.

```bash
ssh core@10.10.10.50 \
  'K="sudo kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml"; $K -n notifications logs deployment/apprise-alertmanager-webhook --since=5m; $K -n notifications logs deployment/apprise --since=5m'
```

Expected: no HTTP 424, invalid YAML, or notification-delivery warning for the synthetic request.

- [ ] **Step 4: Obtain ntfy receipt confirmation**

Ask the operator to confirm receipt of the `SyntheticTest` notification before closing issue #117.
