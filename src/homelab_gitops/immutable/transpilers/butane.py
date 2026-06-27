import subprocess
import yaml
import shutil
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.immutable.transpilers.base import Transpiler
from homelab_gitops.drivers.exceptions import ExecutionError

class ButaneTranspiler(Transpiler):
    def transpile(self, profile: NodeProfile) -> str:
        butane_path = shutil.which("butane")
        if not butane_path:
            raise ExecutionError("butane not found in PATH")

        # Determine network properties
        ip = profile.deployment.get("ip_address")
        netmask = profile.deployment.get("ipv4_netmask", 24)
        gateway = profile.deployment.get("ipv4_gateway")
        dns_servers = profile.deployment.get("dns_servers", [])

        files = [
            {
                "path": "/etc/hostname",
                "mode": 420,  # 0644 in octal
                "contents": {"inline": profile.deployment.get("hostname", profile.name)}
            }
        ]

        # Add static IP configuration if specified
        if ip and gateway:
            dns_str = ";".join(dns_servers) + ";" if dns_servers else ""

            nm_connection = f"""[connection]
id=ens192
type=ethernet
interface-name=ens192

[ipv4]
method=manual
addresses={ip}/{netmask}
gateway={gateway}
dns={dns_str}
"""
            files.append({
                "path": "/etc/NetworkManager/system-connections/ens192.nmconnection",
                "mode": 384,  # 0600 in octal - important for NetworkManager keyfiles
                "contents": {"inline": nm_connection}
            })

        butane_yaml = {
            "variant": "fcos",
            "version": "1.5.0",
            "storage": {
                "files": files
            },
            "passwd": {"users": [{"name": "core", "ssh_authorized_keys": []}]}
        }

        # If it's a k3s server, inject the installation unit
        if "k3s_server" in profile.deployment.get("tags", []):
            butane_yaml["systemd"] = {
                "units": [
                    {
                        "name": "install-k3s.service",
                        "enabled": True,
                        "contents": "[Unit]\nDescription=Install K3s\nWants=network-online.target\nAfter=network-online.target\nConditionPathExists=!/usr/local/bin/k3s\n\n[Service]\nType=oneshot\nEnvironment=INSTALL_K3S_VERSION=v1.35.5+k3s1\nExecStart=/usr/bin/curl -sfL https://get.k3s.io -o /tmp/k3s-install.sh\nExecStartPost=/bin/sh /tmp/k3s-install.sh server --write-kubeconfig-mode 0644\n\n[Install]\nWantedBy=multi-user.target\n"
                    }
                ]
            }
            # Inject ArgoCD bootstrap manifests
            files.append({
                "path": "/var/lib/rancher/k3s/server/manifests/argocd.yaml",
                "mode": 420,  # 0644
                "contents": {"inline": """apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: argocd
  namespace: kube-system
spec:
  chart: argo-cd
  repo: https://argoproj.github.io/argo-helm
  targetNamespace: argocd
  createNamespace: true
"""}
            })

            files.append({
                "path": "/var/lib/rancher/k3s/server/manifests/argocd-root-app.yaml",
                "mode": 420,  # 0644
                "contents": {"inline": """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: k3s-01
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/echoares-lab/homelab-gitops.git
    targetRevision: production
    path: kubernetes/clusters/k3s-01
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"""}
            })


        input_data = yaml.dump(butane_yaml).encode('utf-8')

        result = subprocess.run([butane_path, "--strict"], input=input_data, capture_output=True)
        if result.returncode != 0:
            raise ExecutionError(f"Butane failed: {result.stderr.decode('utf-8')}")

        return result.stdout.decode('utf-8')
