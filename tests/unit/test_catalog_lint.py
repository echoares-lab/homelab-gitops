"""Unit tests for scripts/catalog_lint.py (Epic 2, E2.T4).

Every rule gets a passing fixture and a failing fixture. The last two tests are
the ones that matter operationally: the real
``config/estate_inventory.yaml`` must lint clean, and the CLI must exit 1 when
it does not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.catalog_lint import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    build_entities,
    format_json,
    format_text,
    has_errors,
    lint_estate,
    lint_file,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CATALOG = REPO_ROOT / "config" / "estate_inventory.yaml"


def minimal_catalog() -> dict:
    """A catalog that passes every rule; each test perturbs one thing."""
    return {
        "metadata": {
            "title": "Test estate",
            "authoritative_source": "config/estate_inventory.yaml",
            "version": "2.0.0",
            "default_owner": "echoares-lab",
        },
        "network": {
            "firewall_gateway": {
                "name": "pfsense",
                "role": "Perimeter firewall",
                "lan_ipv4": "10.10.10.1",
                "lan_mac": "00:50:56:9F:79:B2",
            },
            "dns_dhcp_server": {
                "name": "dns-01",
                "role": "DNS & DHCP",
                "ipv4": "10.10.10.2",
            },
            "switches": [
                {
                    "name": "sw-core-01",
                    "role": "Core switch",
                    "interfaces": {
                        "vlan200": {"ipv4": "10.10.10.4"},
                        "loopback0": {"ipv4": "10.1.0.1"},
                    },
                }
            ],
            "access_points": [
                {"name": "ap-01", "role": "Wi-Fi 6 AP", "ipv4": "10.10.10.6"}
            ],
        },
        "physical_servers": [
            {
                "id": "srv-01",
                "name": "esxi-01",
                "role": "Hypervisor",
                "mgmt_ipv4": "10.10.10.11",
                "bmc": {
                    "ipv4_reserved": "10.10.10.10",
                    "current_dhcp_lease": "10.10.10.104",
                },
                "hosted_vms": ["HOMELAB (vm-7030, 10.10.10.30)"],
            }
        ],
        "storage": {
            "appliance": {
                "name": "TRUENAS",
                "role": "ZFS storage",
                "ipv4": "10.10.10.20",
                "mac": "00:50:56:A1:79:C7",
            }
        },
        "virtual_machines": [
            {
                "name": "TRUENAS.PLEXPLEASE.COM",
                "role": "ZFS storage",
                "power_state": "poweredOn",
                "primary_ipv4": "10.10.10.20",
                "mac": "00:50:56:A1:79:C7",
            },
            {
                "name": "k3s-01",
                "role": "Kubernetes node",
                "power_state": "poweredOn",
                "primary_ipv4": "10.10.10.50",
            },
            {
                "name": "HOMELAB",
                "role": "Legacy Docker host",
                "power_state": "tombstoned",
                "tombstoned": "2026-09-14",
                "primary_ipv4": "10.10.10.30",
            },
        ],
        "kubernetes_clusters": [
            {
                "name": "k3s-01",
                "role": "Production cluster",
                "control_plane_ip": "10.10.10.50",
                "reverse_proxied_external_services": [
                    {
                        "ingress": "pfsense.infra.plexplease.com",
                        "target": "10.10.10.1:443",
                    },
                    {
                        "ingress": "switch.infra.plexplease.com",
                        "target": "10.10.10.4:80 (switch OOB is 10.10.10.146)",
                    },
                ],
            }
        ],
        "docker_hosts": [
            {"host_name": "esxi-01", "role": "Docker host", "ipv4": "10.10.10.11"}
        ],
        "discrepancies_and_resolutions": [
            {
                "id": "DISC-01",
                "title": "prose mentioning 10.10.10.1 and 10.10.10.20 twice",
                "resolution": "Prose is not a declaration; 10.10.10.50 appears here too.",
            }
        ],
    }


def rules(findings, rule=None, severity=None):
    """Filter helper: the rule names present, or the findings for one rule."""
    result = findings
    if rule is not None:
        result = [f for f in result if f.rule == rule]
    if severity is not None:
        result = [f for f in result if f.severity == severity]
    return result


# --------------------------------------------------------------------------
# baseline
# --------------------------------------------------------------------------


def test_minimal_catalog_is_clean():
    assert lint_estate(minimal_catalog()) == []


def test_prose_addresses_are_not_declarations():
    """hosted_vms strings and discrepancy prose repeat addresses constantly."""
    catalog = minimal_catalog()
    entities = build_entities(catalog)
    declared = {address for entity in entities for address, _ in entity.addresses}
    # .30 appears only in a hosted_vms string and on the tombstone.
    assert "10.10.10.146" not in declared
    assert declared == {
        "10.10.10.1",
        "10.10.10.2",
        "10.10.10.4",
        "10.1.0.1",
        "10.10.10.6",
        "10.10.10.11",
        "10.10.10.10",
        "10.10.10.20",
        "10.10.10.50",
        "10.10.10.30",
    }


def test_bmc_current_dhcp_lease_is_not_a_declaration():
    """A lease observed today is not a claim on the address."""
    entities = build_entities(minimal_catalog())
    declared = {address for entity in entities for address, _ in entity.addresses}
    assert "10.10.10.104" not in declared


# --------------------------------------------------------------------------
# (f) sanity rules
# --------------------------------------------------------------------------


def test_parse_error_on_non_mapping():
    findings = lint_estate(["not", "a", "mapping"])
    assert [f.rule for f in findings] == ["parse_error"]
    assert has_errors(findings)


def test_metadata_wrong_authoritative_source_fails():
    catalog = minimal_catalog()
    catalog["metadata"]["authoritative_source"] = "config/estate_inventory.json"
    findings = rules(lint_estate(catalog), "metadata")
    assert len(findings) == 1
    assert "authoritative_source" in findings[0].path


def test_metadata_missing_version_fails():
    catalog = minimal_catalog()
    del catalog["metadata"]["version"]
    assert rules(lint_estate(catalog), "metadata")


def test_metadata_missing_entirely_fails():
    catalog = minimal_catalog()
    del catalog["metadata"]
    assert rules(lint_estate(catalog), "metadata")


# --------------------------------------------------------------------------
# (a) duplicate_ip
# --------------------------------------------------------------------------


def test_duplicate_ip_across_two_different_entities_is_an_error():
    catalog = minimal_catalog()
    catalog["virtual_machines"].append(
        {
            "name": "rogue-01",
            "role": "Rogue VM",
            "power_state": "poweredOn",
            "primary_ipv4": "10.10.10.11",
        }
    )
    findings = rules(lint_estate(catalog), "duplicate_ip")
    assert len(findings) == 1
    assert "10.10.10.11" in findings[0].message
    assert findings[0].severity == SEVERITY_ERROR


def test_same_entity_repeat_by_matching_name_is_legitimate():
    """VM k3s-01 and cluster k3s-01 both hold 10.10.10.50."""
    assert rules(lint_estate(minimal_catalog()), "duplicate_ip") == []


def test_same_entity_repeat_by_matching_mac_is_legitimate():
    """storage.appliance TRUENAS and VM TRUENAS.PLEXPLEASE.COM share a MAC."""
    catalog = minimal_catalog()
    catalog["storage"]["appliance"]["name"] = "nas-box"  # names no longer match
    assert rules(lint_estate(catalog), "duplicate_ip") == []


def test_same_entity_repeat_by_first_fqdn_label_is_legitimate():
    catalog = minimal_catalog()
    catalog["storage"]["appliance"]["name"] = "nas-box"
    del catalog["storage"]["appliance"]["mac"]
    catalog["storage"]["appliance"]["fqdn"] = "truenas.plexplease.com"
    assert rules(lint_estate(catalog), "duplicate_ip") == []


def test_unprovable_repeat_needs_same_as():
    catalog = minimal_catalog()
    appliance = catalog["storage"]["appliance"]
    appliance["name"] = "nas-box"
    del appliance["mac"]
    assert rules(lint_estate(catalog), "duplicate_ip"), "should fail without proof"

    appliance["same_as"] = "virtual_machines/TRUENAS.PLEXPLEASE.COM"
    assert rules(lint_estate(catalog), "duplicate_ip") == []


def test_same_as_pointing_at_the_wrong_section_does_not_reconcile():
    catalog = minimal_catalog()
    appliance = catalog["storage"]["appliance"]
    appliance["name"] = "nas-box"
    del appliance["mac"]
    appliance["same_as"] = "physical_servers/TRUENAS.PLEXPLEASE.COM"
    assert rules(lint_estate(catalog), "duplicate_ip")


def test_tombstoned_entity_is_excluded_from_uniqueness():
    """A second live claim on the tombstone's address must not read as a dup."""
    catalog = minimal_catalog()
    catalog["virtual_machines"].append(
        {
            "name": "reuse-01",
            "role": "Reuses a spent address",
            "power_state": "poweredOn",
            "primary_ipv4": "10.10.10.30",
        }
    )
    findings = lint_estate(catalog)
    assert rules(findings, "duplicate_ip") == []
    spent = rules(findings, "spent_address")
    assert len(spent) == 1
    assert spent[0].severity == SEVERITY_WARNING
    assert not has_errors(findings)


def test_two_tombstones_on_one_address_are_not_a_duplicate():
    catalog = minimal_catalog()
    catalog["virtual_machines"].append(
        {
            "name": "HOMELAB-OLD",
            "role": "Older legacy host",
            "power_state": "tombstoned",
            "primary_ipv4": "10.10.10.30",
        }
    )
    assert rules(lint_estate(catalog), "duplicate_ip") == []


# --------------------------------------------------------------------------
# (b) missing_role
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda c: c["network"]["firewall_gateway"].pop("role"), id="firewall"
        ),
        pytest.param(lambda c: c["network"]["switches"][0].pop("role"), id="switch"),
        pytest.param(lambda c: c["network"]["access_points"][0].pop("role"), id="ap"),
        pytest.param(lambda c: c["physical_servers"][0].pop("role"), id="physical"),
        pytest.param(lambda c: c["storage"]["appliance"].pop("role"), id="storage"),
        pytest.param(lambda c: c["virtual_machines"][0].pop("role"), id="vm"),
        pytest.param(lambda c: c["kubernetes_clusters"][0].pop("role"), id="cluster"),
        pytest.param(lambda c: c["docker_hosts"][0].pop("role"), id="docker"),
    ],
)
def test_missing_role_is_an_error_in_every_section(mutate):
    catalog = minimal_catalog()
    mutate(catalog)
    findings = rules(lint_estate(catalog), "missing_role")
    assert len(findings) == 1
    assert findings[0].severity == SEVERITY_ERROR


def test_empty_role_counts_as_missing():
    catalog = minimal_catalog()
    catalog["virtual_machines"][0]["role"] = "   "
    assert rules(lint_estate(catalog), "missing_role")


def test_tombstoned_entities_still_need_a_role():
    catalog = minimal_catalog()
    del catalog["virtual_machines"][2]["role"]
    findings = rules(lint_estate(catalog), "missing_role")
    assert len(findings) == 1
    assert "HOMELAB" in findings[0].message


# --------------------------------------------------------------------------
# (c) missing_owner
# --------------------------------------------------------------------------


def test_default_owner_covers_every_entity():
    assert rules(lint_estate(minimal_catalog()), "missing_owner") == []


def test_no_default_owner_and_no_entity_owner_is_an_error():
    catalog = minimal_catalog()
    del catalog["metadata"]["default_owner"]
    findings = rules(lint_estate(catalog), "missing_owner")
    assert len(findings) == len(build_entities(catalog))
    assert all(f.severity == SEVERITY_ERROR for f in findings)


def test_per_entity_owner_satisfies_the_rule_without_a_default():
    catalog = minimal_catalog()
    del catalog["metadata"]["default_owner"]
    for entity in build_entities(catalog):
        entity.data["owner"] = "someone@example.invalid"
    assert rules(lint_estate(catalog), "missing_owner") == []


# --------------------------------------------------------------------------
# (d) inline_credential
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key,value",
    [
        ("password", "hunter2-correct-horse"),
        ("api_key", "PLACEHOLDER-not-a-real-key"),
        ("apikey", "PLACEHOLDER-not-a-real-key"),
        ("private_key", "MIIEpAIBAAKCAQEA"),
        ("tsig_key", "c2VjcmV0"),
        ("client_secret", "s3cr3t-value"),
        ("auth_token", "t0ken-value"),
    ],
)
def test_credential_keys_with_literal_values_are_errors(key, value):
    catalog = minimal_catalog()
    catalog["virtual_machines"][0][key] = value
    findings = rules(lint_estate(catalog), "inline_credential")
    assert len(findings) == 1
    assert findings[0].severity == SEVERITY_ERROR


@pytest.mark.parametrize(
    "value",
    [
        "op://homelab/technitium/password",
        "kv/homelab/dns/technitium#password",
        "bao:secret/data/homelab/dns#password",
        "${TECHNITIUM_PASSWORD}",
        "$TECHNITIUM_PASSWORD",
    ],
)
def test_secret_references_do_not_trip_the_rule(value):
    catalog = minimal_catalog()
    catalog["virtual_machines"][0]["password"] = value
    assert rules(lint_estate(catalog), "inline_credential") == []


@pytest.mark.parametrize(
    "value",
    [
        "-----BEGIN RSA PRIVATE KEY-----",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9abcdefgh",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_" + "a" * 36,
        "glpat-" + "a" * 20,
        "hvs." + "A" * 24,
        "xoxb-123456789012-abcdefghijkl",
    ],
)
def test_credential_value_patterns_are_errors_under_any_key(value):
    catalog = minimal_catalog()
    catalog["virtual_machines"][0]["notes"] = value
    findings = rules(lint_estate(catalog), "inline_credential")
    assert len(findings) == 1


def test_high_entropy_blob_in_a_plain_field_is_an_error():
    catalog = minimal_catalog()
    catalog["virtual_machines"][0]["notes"] = "aGVsbG8xMjM0NTY3ODkwYWJjZGVmZ2hpams5OTk5"
    assert rules(lint_estate(catalog), "inline_credential")


def test_vault_prose_in_a_role_does_not_trip_the_rule():
    """`role: OpenBao / HashiCorp Vault secrets backend` is a description."""
    catalog = minimal_catalog()
    catalog["virtual_machines"][0]["role"] = "OpenBao / HashiCorp Vault secrets backend"
    assert rules(lint_estate(catalog), "inline_credential") == []


def test_identifiers_and_build_strings_do_not_trip_the_rule():
    catalog = minimal_catalog()
    catalog["physical_servers"][0]["hardware"] = {
        "system_uuid": "4c4c4544-0053-4810-804c-b9c04f503933",
        "os": "SONiC.202511-n3224t-slim2.0-39ddd324e (Debian 13.6)",
        "build": "25205845",
        "image": "public.ecr.aws/d3g4m7o9/epc-api:1.9.0",
    }
    assert rules(lint_estate(catalog), "inline_credential") == []


def test_empty_credential_value_is_not_a_finding():
    catalog = minimal_catalog()
    catalog["virtual_machines"][0]["password"] = ""
    assert rules(lint_estate(catalog), "inline_credential") == []


# --------------------------------------------------------------------------
# (e) stale_target
# --------------------------------------------------------------------------


def test_annotated_target_parses_and_passes():
    """`10.10.10.4:80 (switch OOB is 10.10.10.146)` is a valid target."""
    assert rules(lint_estate(minimal_catalog()), "stale_target") == []


def test_target_on_a_tombstoned_address_is_an_error():
    catalog = minimal_catalog()
    catalog["kubernetes_clusters"][0]["reverse_proxied_external_services"].append(
        {"ingress": "plex.infra.plexplease.com", "target": "10.10.10.30:32400"}
    )
    findings = rules(lint_estate(catalog), "stale_target")
    assert len(findings) == 1
    assert "tombstoned" in findings[0].message


def test_target_on_an_undeclared_address_is_an_error():
    catalog = minimal_catalog()
    catalog["kubernetes_clusters"][0]["reverse_proxied_external_services"].append(
        {"ingress": "ghost.infra.plexplease.com", "target": "10.10.10.222:8080"}
    )
    findings = rules(lint_estate(catalog), "stale_target")
    assert len(findings) == 1
    assert "not declared" in findings[0].message


def test_unparseable_target_is_an_error():
    catalog = minimal_catalog()
    catalog["kubernetes_clusters"][0]["reverse_proxied_external_services"].append(
        {"ingress": "bad.infra.plexplease.com", "target": "http://10.10.10.1/"}
    )
    findings = rules(lint_estate(catalog), "stale_target")
    assert len(findings) == 1
    assert "does not parse" in findings[0].message


def test_missing_target_is_an_error():
    catalog = minimal_catalog()
    catalog["kubernetes_clusters"][0]["reverse_proxied_external_services"].append(
        {"ingress": "bad.infra.plexplease.com"}
    )
    assert rules(lint_estate(catalog), "stale_target")


# --------------------------------------------------------------------------
# reporting + file handling
# --------------------------------------------------------------------------


def test_format_json_is_machine_readable():
    catalog = minimal_catalog()
    del catalog["virtual_machines"][0]["role"]
    findings = lint_estate(catalog)
    payload = json.loads(format_json(findings, "x.yaml"))
    assert payload["errors"] == 1
    assert payload["findings"][0]["rule"] == "missing_role"
    assert set(payload["findings"][0]) == {"rule", "severity", "path", "message"}


def test_format_text_reports_a_clean_file():
    assert "0 findings" in format_text([], "x.yaml")


def test_lint_file_on_a_missing_path_is_a_parse_error(tmp_path):
    findings = lint_file(tmp_path / "nope.yaml")
    assert [f.rule for f in findings] == ["parse_error"]


def test_lint_file_on_malformed_yaml_is_a_parse_error(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("metadata: [unclosed\n")
    findings = lint_file(bad)
    assert [f.rule for f in findings] == ["parse_error"]


# --------------------------------------------------------------------------
# the real catalog, and the CLI contract
# --------------------------------------------------------------------------


def test_real_estate_inventory_lints_clean():
    """The gate this task exists for: config/estate_inventory.yaml has 0 errors."""
    findings = lint_file(REAL_CATALOG)
    assert findings == [], format_text(findings, str(REAL_CATALOG))


def test_real_estate_inventory_has_no_reverse_proxied_target_on_the_tombstone():
    estate = yaml.safe_load(REAL_CATALOG.read_text())
    cluster = estate["kubernetes_clusters"][0]
    targets = [
        service["target"] for service in cluster["reverse_proxied_external_services"]
    ]
    assert not any(target.startswith("10.10.10.30:") for target in targets)
    assert "10.10.10.40:8201" in targets
    plex = [d for d in cluster["core_deployments"] if d["name"] == "plex"]
    assert plex and plex[0]["namespace"] == "plex"


def test_cli_exits_zero_on_the_real_catalog(capsys):
    assert main([str(REAL_CATALOG)]) == 0


def test_cli_exits_one_on_a_failing_fixture(tmp_path, capsys):
    catalog = minimal_catalog()
    catalog["virtual_machines"].append(
        {
            "name": "rogue-01",
            "role": "Rogue VM",
            "power_state": "poweredOn",
            "primary_ipv4": "10.10.10.11",
        }
    )
    fixture = tmp_path / "duplicate.yaml"
    fixture.write_text(yaml.safe_dump(catalog))
    assert main([str(fixture), "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"][0]["rule"] == "duplicate_ip"


def test_cli_subprocess_exit_code_is_one_on_a_duplicate_ip(tmp_path):
    """The CI job's actual contract: a non-zero process exit."""
    catalog = minimal_catalog()
    catalog["virtual_machines"].append(
        {
            "name": "rogue-01",
            "role": "Rogue VM",
            "power_state": "poweredOn",
            "primary_ipv4": "10.10.10.11",
        }
    )
    fixture = tmp_path / "duplicate.yaml"
    fixture.write_text(yaml.safe_dump(catalog))
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "catalog_lint.py"), str(fixture)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "duplicate_ip" in completed.stdout
