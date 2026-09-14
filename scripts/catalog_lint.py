#!/usr/bin/env python3
"""Catalog lint for the authoritative estate record.

``config/estate_inventory.yaml`` is the hand-maintained source of truth for the
estate (see ``scripts/build_estate_inventory.py``). Nothing enforced its
internal consistency until this module: an address could be claimed twice, an
entity could carry no role and no owner, a credential could be pasted inline,
and a reverse-proxied target could go on pointing at a machine that had been
tombstoned. All four had happened by the 2026-09-14 audit.

Rule table
----------
======================  ========  ======================================================
rule                    severity  what it enforces
======================  ========  ======================================================
``parse_error``         error     the file is readable and parses to a mapping
``metadata``            error     ``authoritative_source`` is this file; ``version`` set
``duplicate_ip``        error     an address is DECLARED by at most one entity
``spent_address``       warning   a live entity reuses an address a tombstone still holds
``missing_role``        error     every catalogued entity carries a non-empty ``role``
``missing_owner``       error     ``entity.owner`` or ``metadata.default_owner`` resolves
``inline_credential``   error     no literal secret in a key or a value
``stale_target``        error     every reverse-proxied target is ``ip:port`` on a live
                                  declared entity
======================  ========  ======================================================

What counts as an address DECLARATION
-------------------------------------
Only the structured keys in :data:`ADDRESS_KEYS`, reached through the section
map in :data:`SECTIONS` (plus ``bmc.ipv4_reserved`` and ``interfaces.*.ipv4``).
Prose fields -- ``hosted_vms`` strings, ``notes``, ``*_note``, ``description``
and the whole ``discrepancies_and_resolutions`` section -- mention addresses by
the dozen and are never declarations. ``bmc.current_dhcp_lease`` is an observed
lease, not a declaration, and is deliberately excluded too.

Legitimate cross-section repeats
--------------------------------
One machine is often catalogued twice on purpose: TrueNAS is both
``storage.appliance`` and a ``virtual_machines`` entry. Two records may share an
address only when they are provably the same entity:

1. a shared identity label -- case-insensitive equality of any
   ``name``/``host_name``/``id`` or the first label of any ``fqdn``; or
2. a shared MAC address; or
3. an explicit ``same_as: <section>/<name>`` on either record.

``same_as`` exists so that a pair the data does not self-identify (the
``talos-cluster`` entry versus the ``talos-fty-fw0`` host that runs it) is
reconciled in the *data*, where a reviewer sees it, rather than special-cased in
this code.

Ownership
---------
The record had no owner field at all. ``metadata.default_owner`` supplies the
fallback for the whole estate and ``owner:`` on any entity overrides it.

Usage
-----
``python3 scripts/catalog_lint.py [path] [--format text|json]``; exit 1 if any
finding has severity ``error``, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import yaml

DEFAULT_PATH = "config/estate_inventory.yaml"
EXPECTED_AUTHORITATIVE_SOURCE = "config/estate_inventory.yaml"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

#: Keys whose value is an address DECLARATION by the entity that carries them.
ADDRESS_KEYS = (
    "ipv4",
    "primary_ipv4",
    "lan_ipv4",
    "wan_ipv4",
    "mgmt_ipv4",
    "control_plane_ip",
)

#: Keys under ``bmc:`` that declare an address. ``current_dhcp_lease`` is an
#: observation of what DHCP handed out today, not a claim on the address.
BMC_ADDRESS_KEYS = ("ipv4_reserved",)

#: Keys carrying an identity label for an entity.
IDENTITY_KEYS = ("name", "host_name", "id")

#: Keys carrying a fully-qualified name; the first label identifies the entity.
FQDN_KEYS = ("fqdn", "fqdn_bench", "fqdn_mgmt", "node_name")

#: Keys carrying a MAC address.
MAC_KEYS = ("mac", "lan_mac", "wan_mac", "mgmt_mac")


@dataclass(frozen=True)
class SectionSpec:
    """Where catalogued entities live, and how that container is shaped."""

    path: tuple[str, ...]
    is_list: bool

    @property
    def label(self) -> str:
        return ".".join(self.path)


#: Every container of catalogued entities. Anything outside this map is prose or
#: derived data and is never scanned for declarations, roles or owners.
SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec(("network", "firewall_gateway"), is_list=False),
    SectionSpec(("network", "dns_dhcp_server"), is_list=False),
    SectionSpec(("network", "switches"), is_list=True),
    SectionSpec(("network", "access_points"), is_list=True),
    SectionSpec(("physical_servers",), is_list=True),
    SectionSpec(("storage", "appliance"), is_list=False),
    SectionSpec(("virtual_machines",), is_list=True),
    SectionSpec(("kubernetes_clusters",), is_list=True),
    SectionSpec(("docker_hosts",), is_list=True),
)

#: Mapping keys that name a credential. A non-empty literal under one of these
#: is a secret in version control.
CREDENTIAL_KEY_RE = re.compile(
    r"(?:^|_)(?:password|passwd|pwd|secret|token|api_?key|apikey|access_key"
    r"|private_key|privkey|tsig|tsig_key|credential|credentials|client_secret"
    r"|auth_token|bearer)(?:_|$)",
    re.IGNORECASE,
)

#: Values that are references to a secret store, never the secret itself.
SECRET_REFERENCE_RE = re.compile(
    r"^(?:op://|kv/|kv-v2/|bao:|vault:|secret://|env:|file:)"
    r"|^\$\{[^}]+\}$|^\$[A-Z_][A-Z0-9_]*$",
    re.IGNORECASE,
)

#: Value shapes that are a leaked credential wherever they appear.
CREDENTIAL_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PEM private key header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("HTTP Bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]{16,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9\-_]{16,}\b")),
    ("OpenBao/Vault service token", re.compile(r"\bhvs\.[A-Za-z0-9\-_]{16,}\b")),
    ("Slack token", re.compile(r"\bxox[bp]-[A-Za-z0-9-]{10,}\b")),
)

#: A standalone ≥32-character base64 or hex blob. Anchored on word boundaries and
#: required to mix character classes so that model strings, build numbers and DMI
#: UUIDs (which carry dashes) do not trip it.
HIGH_ENTROPY_RE = re.compile(
    r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])"
)

#: ``10.10.10.4:80 (switch OOB is 10.10.10.146)`` -- the annotation is commentary.
TARGET_RE = re.compile(
    r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3}):(?P<port>\d{1,5})(?:\s*\(.*\))?$"
)

IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

#: Keys whose value is prose. Never scanned for declarations.
PROSE_KEYS = frozenset(
    {
        "notes",
        "note",
        "description",
        "documented",
        "empirical_evidence",
        "resolution",
        "evidence",
        "maintenance",
        "hosted_vms",
        "dual_boot",
        "ipv4_assignment",
    }
)


@dataclass(frozen=True)
class Finding:
    """One machine-readable lint result."""

    rule: str
    severity: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }


@dataclass
class Entity:
    """A catalogued thing, with the identity evidence used to reconcile it."""

    section: str
    path: str
    data: dict[str, Any]
    labels: frozenset[str] = field(default_factory=frozenset)
    macs: frozenset[str] = field(default_factory=frozenset)
    same_as: str | None = None
    tombstoned: bool = False
    addresses: tuple[tuple[str, str], ...] = ()

    @property
    def display(self) -> str:
        for key in IDENTITY_KEYS:
            value = self.data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return self.path


class CatalogLintError(Exception):
    """The catalog could not be read at all."""


def _first_label(value: str) -> str:
    return value.strip().split(".")[0].casefold()


def _normalise_mac(value: str) -> str:
    return value.strip().casefold()


def _same_as_key(section: str, label: str) -> str:
    return f"{section}/{label.casefold()}"


def _iter_section_entities(
    estate: dict[str, Any],
) -> Iterator[tuple[SectionSpec, str, dict]]:
    """Yield ``(spec, path, mapping)`` for every catalogued entity."""
    for spec in SECTIONS:
        node: Any = estate
        for key in spec.path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if node is None:
            continue
        if spec.is_list:
            if not isinstance(node, list):
                continue
            for index, item in enumerate(node):
                if isinstance(item, dict):
                    yield spec, f"{spec.label}[{index}]", item
        elif isinstance(node, dict):
            yield spec, spec.label, node


def _entity_addresses(entity: dict[str, Any], path: str) -> list[tuple[str, str]]:
    """Collect ``(address, yaml path)`` declarations for one entity."""
    found: list[tuple[str, str]] = []
    for key in ADDRESS_KEYS:
        value = entity.get(key)
        if isinstance(value, str) and IPV4_RE.match(value.strip()):
            found.append((value.strip(), f"{path}.{key}"))

    bmc = entity.get("bmc")
    if isinstance(bmc, dict):
        for key in BMC_ADDRESS_KEYS:
            value = bmc.get(key)
            if isinstance(value, str) and IPV4_RE.match(value.strip()):
                found.append((value.strip(), f"{path}.bmc.{key}"))

    interfaces = entity.get("interfaces")
    if isinstance(interfaces, dict):
        for iface_name, iface in interfaces.items():
            if not isinstance(iface, dict):
                continue
            value = iface.get("ipv4")
            if isinstance(value, str) and IPV4_RE.match(value.strip()):
                found.append((value.strip(), f"{path}.interfaces.{iface_name}.ipv4"))
    return found


def build_entities(estate: dict[str, Any]) -> list[Entity]:
    """Build the reconciled entity list the address and role rules run over."""
    entities: list[Entity] = []
    for spec, path, data in _iter_section_entities(estate):
        labels: set[str] = set()
        for key in IDENTITY_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                labels.add(_first_label(value))
        for key in FQDN_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                labels.add(_first_label(value))

        macs: set[str] = set()
        for key in MAC_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                macs.add(_normalise_mac(value))
        bmc = data.get("bmc")
        if isinstance(bmc, dict) and isinstance(bmc.get("mac"), str):
            macs.add(_normalise_mac(bmc["mac"]))

        same_as = data.get("same_as")
        entities.append(
            Entity(
                section=spec.label,
                path=path,
                data=data,
                labels=frozenset(labels),
                macs=frozenset(macs),
                same_as=same_as.strip() if isinstance(same_as, str) else None,
                tombstoned=_is_tombstoned(data),
                addresses=tuple(_entity_addresses(data, path)),
            )
        )
    return entities


def _is_tombstoned(data: dict[str, Any]) -> bool:
    if str(data.get("power_state", "")).strip().casefold() == "tombstoned":
        return True
    return bool(data.get("tombstoned"))


def _same_entity(left: Entity, right: Entity) -> bool:
    """True when two records provably describe the same machine."""
    if left.labels & right.labels:
        return True
    if left.macs & right.macs:
        return True
    for a, b in ((left, right), (right, left)):
        if not a.same_as:
            continue
        section, _, label = a.same_as.partition("/")
        if not label:
            continue
        if section.strip() == b.section and _first_label(label) in b.labels:
            return True
    return False


def _group_same(entities: Sequence[Entity]) -> list[list[Entity]]:
    """Partition entities into groups that are provably the same machine."""
    groups: list[list[Entity]] = []
    for entity in entities:
        for group in groups:
            if any(_same_entity(entity, member) for member in group):
                group.append(entity)
                break
        else:
            groups.append([entity])
    return groups


def check_metadata(estate: dict[str, Any]) -> list[Finding]:
    """Rule ``metadata``: the file says what it is."""
    findings: list[Finding] = []
    metadata = estate.get("metadata")
    if not isinstance(metadata, dict):
        return [
            Finding(
                "metadata",
                SEVERITY_ERROR,
                "metadata",
                "metadata is missing or is not a mapping.",
            )
        ]
    declared = metadata.get("authoritative_source")
    if declared != EXPECTED_AUTHORITATIVE_SOURCE:
        findings.append(
            Finding(
                "metadata",
                SEVERITY_ERROR,
                "metadata.authoritative_source",
                f"is {declared!r}, expected {EXPECTED_AUTHORITATIVE_SOURCE!r}.",
            )
        )
    if not str(metadata.get("version", "")).strip():
        findings.append(
            Finding(
                "metadata", SEVERITY_ERROR, "metadata.version", "is missing or empty."
            )
        )
    return findings


def check_duplicate_ips(entities: Sequence[Entity]) -> list[Finding]:
    """Rules ``duplicate_ip`` and ``spent_address``."""
    by_address: dict[str, list[tuple[Entity, str]]] = {}
    for entity in entities:
        for address, path in entity.addresses:
            by_address.setdefault(address, []).append((entity, path))

    findings: list[Finding] = []
    for address in sorted(by_address):
        claims = by_address[address]
        live = [(e, p) for e, p in claims if not e.tombstoned]
        dead = [(e, p) for e, p in claims if e.tombstoned]

        groups = _group_same([entity for entity, _ in live])
        if len(groups) > 1:
            owners = ", ".join(
                sorted(f"{path} ({entity.display})" for entity, path in live)
            )
            findings.append(
                Finding(
                    "duplicate_ip",
                    SEVERITY_ERROR,
                    claims[0][1],
                    f"{address} is declared by {len(groups)} different entities: {owners}. "
                    "If these are one machine, make that provable with a matching "
                    "name/fqdn, a matching mac, or a `same_as: <section>/<name>` field.",
                )
            )
        if live and dead:
            spent = ", ".join(sorted(entity.display for entity, _ in dead))
            findings.append(
                Finding(
                    "spent_address",
                    SEVERITY_WARNING,
                    live[0][1],
                    f"{address} is reused by {live[0][0].display} while tombstoned "
                    f"entity {spent} still records it.",
                )
            )
    return findings


def check_roles_and_owners(
    estate: dict[str, Any], entities: Sequence[Entity]
) -> list[Finding]:
    """Rules ``missing_role`` and ``missing_owner``."""
    metadata = estate.get("metadata")
    default_owner = ""
    if isinstance(metadata, dict):
        default_owner = str(metadata.get("default_owner") or "").strip()

    findings: list[Finding] = []
    for entity in entities:
        role = str(entity.data.get("role") or "").strip()
        if not role:
            findings.append(
                Finding(
                    "missing_role",
                    SEVERITY_ERROR,
                    f"{entity.path}.role",
                    f"{entity.display} has no role. Every catalogued entity must say "
                    "what it is for.",
                )
            )
        owner = str(entity.data.get("owner") or "").strip()
        if not owner and not default_owner:
            findings.append(
                Finding(
                    "missing_owner",
                    SEVERITY_ERROR,
                    f"{entity.path}.owner",
                    f"{entity.display} has no owner and metadata.default_owner is not "
                    "set. Set one or the other.",
                )
            )
    return findings


def _walk_scalars(node: Any, path: str = "") -> Iterator[tuple[str, str | None, Any]]:
    """Yield ``(path, key, value)`` for every scalar in the document."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if isinstance(value, (dict, list)):
                yield from _walk_scalars(value, child)
            else:
                yield child, str(key), value
    elif isinstance(node, list):
        for index, value in enumerate(node):
            child = f"{path}[{index}]"
            if isinstance(value, (dict, list)):
                yield from _walk_scalars(value, child)
            else:
                yield child, None, value


def _is_reference(value: str) -> bool:
    return bool(SECRET_REFERENCE_RE.search(value.strip()))


def check_inline_credentials(estate: dict[str, Any]) -> list[Finding]:
    """Rule ``inline_credential``."""
    findings: list[Finding] = []
    for path, key, value in _walk_scalars(estate):
        if value is None:
            continue
        text = str(value)
        if key and CREDENTIAL_KEY_RE.search(key) and text.strip():
            if _is_reference(text):
                continue
            findings.append(
                Finding(
                    "inline_credential",
                    SEVERITY_ERROR,
                    path,
                    f"key {key!r} carries a literal value. Store the secret in OpenBao "
                    "and record a reference (op://..., kv/..., bao:..., ${VAR}).",
                )
            )
            continue
        if not isinstance(value, str):
            continue
        for label, pattern in CREDENTIAL_VALUE_PATTERNS:
            if pattern.search(text):
                findings.append(
                    Finding(
                        "inline_credential",
                        SEVERITY_ERROR,
                        path,
                        f"value looks like a {label}.",
                    )
                )
                break
        else:
            if _is_reference(text):
                continue
            for blob in HIGH_ENTROPY_RE.findall(text):
                if _looks_high_entropy(blob):
                    findings.append(
                        Finding(
                            "inline_credential",
                            SEVERITY_ERROR,
                            path,
                            f"value contains a {len(blob)}-character high-entropy blob, "
                            "which is how a key or token looks.",
                        )
                    )
                    break
    return findings


def _looks_high_entropy(blob: str) -> bool:
    """A ≥32-char blob that mixes classes the way a key does, not an identifier."""
    has_lower = any(character.islower() for character in blob)
    has_upper = any(character.isupper() for character in blob)
    has_digit = any(character.isdigit() for character in blob)
    if not has_digit:
        return False
    if not (has_lower and has_upper):
        # A pure-hex blob still reads as a key when it is long and all one case.
        return len(blob) >= 32 and all(c in "0123456789abcdefABCDEF" for c in blob)
    return True


def check_stale_targets(
    estate: dict[str, Any], entities: Sequence[Entity]
) -> list[Finding]:
    """Rule ``stale_target``."""
    live_addresses: set[str] = set()
    dead_addresses: dict[str, str] = {}
    for entity in entities:
        for address, _ in entity.addresses:
            if entity.tombstoned:
                dead_addresses.setdefault(address, entity.display)
            else:
                live_addresses.add(address)

    findings: list[Finding] = []
    clusters = estate.get("kubernetes_clusters")
    if not isinstance(clusters, list):
        return findings

    for index, cluster in enumerate(clusters):
        if not isinstance(cluster, dict):
            continue
        services = cluster.get("reverse_proxied_external_services")
        if not isinstance(services, list):
            continue
        for service_index, service in enumerate(services):
            path = (
                f"kubernetes_clusters[{index}]."
                f"reverse_proxied_external_services[{service_index}].target"
            )
            if not isinstance(service, dict):
                continue
            target = service.get("target")
            if not isinstance(target, str) or not target.strip():
                findings.append(
                    Finding("stale_target", SEVERITY_ERROR, path, "target is missing.")
                )
                continue
            match = TARGET_RE.match(target.strip())
            if not match:
                findings.append(
                    Finding(
                        "stale_target",
                        SEVERITY_ERROR,
                        path,
                        f"{target!r} does not parse as ip:port.",
                    )
                )
                continue
            address = match.group("ip")
            if address in live_addresses:
                continue
            if address in dead_addresses:
                findings.append(
                    Finding(
                        "stale_target",
                        SEVERITY_ERROR,
                        path,
                        f"{address} belongs to tombstoned entity "
                        f"{dead_addresses[address]}; the target is stale.",
                    )
                )
            else:
                findings.append(
                    Finding(
                        "stale_target",
                        SEVERITY_ERROR,
                        path,
                        f"{address} is not declared by any entity in this catalog.",
                    )
                )
    return findings


def lint_estate(estate: Any) -> list[Finding]:
    """Run every rule over an already-parsed catalog."""
    if not isinstance(estate, dict):
        return [
            Finding(
                "parse_error",
                SEVERITY_ERROR,
                "",
                "the catalog did not parse to a mapping.",
            )
        ]
    entities = build_entities(estate)
    findings: list[Finding] = []
    findings.extend(check_metadata(estate))
    findings.extend(check_duplicate_ips(entities))
    findings.extend(check_roles_and_owners(estate, entities))
    findings.extend(check_inline_credentials(estate))
    findings.extend(check_stale_targets(estate, entities))
    return findings


def lint_file(path: str | Path) -> list[Finding]:
    """Parse and lint a catalog file."""
    path = Path(path)
    if not path.exists():
        return [
            Finding("parse_error", SEVERITY_ERROR, str(path), "file does not exist.")
        ]
    try:
        with path.open() as handle:
            estate = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        return [Finding("parse_error", SEVERITY_ERROR, str(path), f"YAML error: {exc}")]
    return lint_estate(estate)


def has_errors(findings: Iterable[Finding]) -> bool:
    """True when at least one finding is an error."""
    return any(finding.severity == SEVERITY_ERROR for finding in findings)


def format_text(findings: Sequence[Finding], path: str) -> str:
    """Human-readable report."""
    if not findings:
        return f"catalog_lint: {path}: 0 findings"
    lines = [f"catalog_lint: {path}"]
    for finding in findings:
        location = finding.path or path
        lines.append(
            f"  {finding.severity.upper():<7} {finding.rule:<18} {location}: {finding.message}"
        )
    errors = sum(1 for finding in findings if finding.severity == SEVERITY_ERROR)
    warnings = len(findings) - errors
    lines.append(f"  {errors} error(s), {warnings} warning(s)")
    return "\n".join(lines)


def format_json(findings: Sequence[Finding], path: str) -> str:
    """Machine-readable report."""
    return json.dumps(
        {
            "path": path,
            "findings": [finding.as_dict() for finding in findings],
            "errors": sum(1 for f in findings if f.severity == SEVERITY_ERROR),
            "warnings": sum(1 for f in findings if f.severity == SEVERITY_WARNING),
        },
        indent=2,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns 1 when any error-severity finding is raised."""
    parser = argparse.ArgumentParser(
        prog="catalog_lint",
        description="Lint the authoritative estate catalog.",
    )
    parser.add_argument("path", nargs="?", default=DEFAULT_PATH)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    path = args.path
    findings = lint_file(path)
    render = format_json if args.format == "json" else format_text
    print(render(findings, str(path)))
    return 1 if has_errors(findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
