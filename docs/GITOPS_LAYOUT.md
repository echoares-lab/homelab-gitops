# GitOps Layout Standard

This document defines the target Kubernetes GitOps directory standard. It is a
documentation-only standard for the current issue; manifests should move to this
layout in later, explicit migration work.

## Target Directory Model

All Kubernetes GitOps content lives under `kubernetes/` and is split by
reconciliation responsibility:

```text
kubernetes/
  bootstrap/
    <cluster>/
      root-apps/
      projects/
  clusters/
    <cluster>/
      kustomization.yaml
      config/
      platform/
      workloads/
  platform/
    <app>/
      base/
      overlays/
        <cluster>/
  workloads/
    <owner>/
      <app>/
        base/
        overlays/
          <cluster>/
```

### `bootstrap/<cluster>/`

Bootstrap resources are the minimum set needed to let the GitOps controller take
over a cluster. This includes Argo CD installation glue when it is managed from
Git, AppProjects, and root Application or ApplicationSet definitions.

Root apps should point at `clusters/<cluster>/` or at explicitly named platform
and workload overlays. Bootstrap resources should not contain routine workload
manifests.

### `clusters/<cluster>/`

Cluster directories are the desired-state entrypoint for one cluster. A cluster
directory owns cluster-specific composition and overrides, such as:

- namespace declarations
- cluster-local secret stores, issuers, ingress hosts, and DNS zones
- references to platform app overlays
- references to workload overlays selected for that cluster

Cluster names use the inventory name, for example `k3s-01`. Keep the root
`kustomization.yaml` readable; it should compose resources rather than becoming
the long-term home for every manifest.

### `platform/<app>/`

Platform apps are shared services that make the cluster usable or govern other
apps. Examples include Argo CD, cert-manager, external-secrets, external-dns,
OpenBao integration, ingress controllers, monitoring agents, policy engines, and
storage controllers.

Each platform app owns its reusable base under `base/` and cluster-specific
differences under `overlays/<cluster>/`. Platform app names use lower-case
kebab-case and should match the upstream or operational service name where
possible, for example `cert-manager` or `external-dns`.

### `workloads/<owner>/<app>/`

Workloads are tenant, product, or homelab services that depend on platform
capabilities. The first path segment after `workloads/` is the owning team,
person, or domain. For a single-operator homelab, use a stable domain owner such
as `home`, `media`, `networking`, or `lab` rather than a personal handle.

Workload app names use lower-case kebab-case. A workload may depend on a
platform app, but platform app directories must not depend on workload content.

## Naming Rules

- Use lower-case kebab-case for directories, Kubernetes resource names, labels,
  and Argo CD Application names.
- Use the inventory cluster name exactly for cluster path segments, for example
  `k3s-01`.
- Name Argo CD Applications as `<cluster>-<scope>-<app>` when they are
  cluster-specific, for example `k3s-01-platform-cert-manager`.
- Name reusable bases after the app, not the cluster.
- Keep secret values out of Git. Git may contain ExternalSecret, SecretStore,
  ClusterSecretStore, and sealed/encrypted secret references, but not plaintext
  credentials.
- Prefer one app per directory. Split a directory when two components have
  different owners, lifecycles, sync waves, or rollback needs.

## Ownership Rules

- `bootstrap/<cluster>/` is owned by the cluster platform operator because it can
  install or redirect the GitOps control plane.
- `clusters/<cluster>/` is owned by the cluster platform operator and records
  what is enabled on that cluster.
- `platform/<app>/` is owned by the operator responsible for that shared
  platform capability.
- `workloads/<owner>/<app>/` is owned by the workload owner named in the path.
- Cross-directory changes should be reviewed by every affected owner. For
  example, a workload PR that also changes `platform/external-dns` needs platform
  owner review.
- A directory owner is responsible for documenting required secrets, DNS names,
  storage classes, and ingress assumptions in that directory's README when those
  assumptions are not obvious from the manifests.

## k3s-01 Layout

The `k3s-01` manifests follow the standard layout. Argo CD should continue to
sync the cluster entrypoint at `kubernetes/clusters/k3s-01/`, which composes the
cluster config and selected platform overlays.

| Current path | Ownership |
| --- | --- |
| `kubernetes/bootstrap/k3s-01/root-apps/` | Bootstrap root Application manifests |
| `kubernetes/clusters/k3s-01/kustomization.yaml` | Cluster composition |
| `kubernetes/clusters/k3s-01/config/namespaces.yaml` | Cluster namespace baseline |
| `kubernetes/platform/argocd/overlays/k3s-01/` | Argo CD platform overlay |
| `kubernetes/platform/cert-manager/overlays/k3s-01/` | cert-manager platform overlay |
| `kubernetes/platform/external-secrets/overlays/k3s-01/` | external-secrets platform overlay |
| `kubernetes/platform/external-dns/overlays/k3s-01/` | external-dns platform overlay |
| `kubernetes/platform/openbao/overlays/k3s-01/` | OpenBao platform integration |

No workload directories are present today. Future application services should be
added under `kubernetes/workloads/<owner>/<app>/` and then referenced by
`kubernetes/clusters/k3s-01/`.
