"""Shared helper for resolving vCenter credentials from OpenBao with loud failures.

This centralizes the logic both Workflow and ImmutableWorkflow use to fetch
vCenter connection details. Unlike the previous inline try/except blocks, this
helper does NOT silently substitute an empty password when OpenBao is
unreachable: if a secret cannot be resolved from OpenBao AND no environment
fallback is present, it raises SecretResolutionError with an actionable message.
"""

import os
from typing import Dict

from homelab_gitops.domain.exceptions import SecretResolutionError

# Map of override key -> (bao URI, environment fallback variable)
_VCENTER_SECRETS = {
    "vcenter_user": (
        "bao://kv/prod/platform/vcenter/VCENTER_USERNAME",
        "VCENTER_USER",
    ),
    "vcenter_password": (
        "bao://kv/prod/platform/vcenter/VCENTER_PASSWORD",
        "VCENTER_PASSWORD",
    ),
    "vcenter_server": (
        "bao://kv/prod/platform/vcenter/VCENTER_SERVER",
        "VCENTER_SERVER",
    ),
}

_REMEDIATION = (
    "Could not resolve vCenter credential '{key}' from OpenBao "
    "({uri}) and no '{env}' environment fallback is set.\n"
    "Authenticate to OpenBao before running this command, e.g.:\n"
    "  export VAULT_ADDR=http://openbao.plexplease.com:8201\n"
    "  bao login   # or: export VAULT_TOKEN=<token>\n"
    "Then verify with:\n"
    "  bao kv get -mount=kv -field={env} prod/platform/vcenter"
)


def resolve_vcenter_credentials(server_fallback: str = "") -> Dict[str, str]:
    """Resolve vCenter user, password, and server.

    Resolution order per secret:
      1. OpenBao via the SecretsDriver (bao:// URI).
      2. The documented environment variable fallback.
      3. For the server only, the provided ``server_fallback`` (profile host).

    Raises:
        SecretResolutionError: if a required secret resolves to an empty value
            from every source. The error names the secret, its bao URI, the env
            var, and the remediation steps.
    """
    from homelab_gitops.drivers.secrets_driver import SecretsDriver
    from homelab_gitops.domain.models import Task as SecretsTask

    resolved: Dict[str, str] = {}

    try:
        secrets_driver = SecretsDriver()
    except Exception:
        secrets_driver = None

    for key, (uri, env_var) in _VCENTER_SECRETS.items():
        value = ""

        if secrets_driver is not None:
            try:
                value = secrets_driver.execute(
                    SecretsTask(type="get", target=uri)
                ).output
            except Exception:
                value = ""

        if not value:
            value = os.environ.get(env_var, "")

        if not value and key == "vcenter_server":
            value = server_fallback

        if not value:
            # vcenter_user has a sane non-secret default; never block on it.
            if key == "vcenter_user":
                value = "administrator@vsphere.local"
            else:
                raise SecretResolutionError(
                    _REMEDIATION.format(key=key, uri=uri, env=env_var)
                )

        resolved[key] = value

    return resolved
