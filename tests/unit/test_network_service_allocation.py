"""Regression tests for NetworkService address allocation and PTR generation.

These cover three defects that reached config/dns_records.csv in production:

1. PTR records were written with parent zone ``10.in-addr.arpa`` (which does not
   exist on the Technitium server) instead of ``10.10.10.in-addr.arpa``, so every
   generated reverse lookup silently failed to resolve.
2. Batch provisioning handed the same address to several hosts, because each
   allocation only consulted the CSV on disk and nothing tracked addresses
   already handed out in the current run.
3. Statically-addressed physical hardware (a core switch, an access point) was
   assigned to VMs, because liveness was inferred from a single ping and the
   devices were absent from the CSV.
"""

from unittest.mock import patch

import pytest

from homelab_gitops.domain.network import NetworkService

CSV_HEADER = (
    "resource_type,name,parent,type,value,ttl,mac_address,network_address,"
    "subnet_mask,start_address,end_address,gateway,comments,depends_on,advanced_json\n"
)


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "dns_records.csv"
    p.write_text(CSV_HEADER)
    return str(p)


def _rows(path, resource_type=None, rec_type=None):
    import csv

    with open(path) as f:
        rows = list(csv.DictReader(f))
    if resource_type:
        rows = [r for r in rows if r["resource_type"] == resource_type]
    if rec_type:
        rows = [r for r in rows if r["type"] == rec_type]
    return rows


def test_ptr_parent_zone_keeps_full_subnet(csv_path):
    """PTR parent must be the /24 reverse zone, not the /8."""
    svc = NetworkService(dns_csv_path=csv_path)
    svc.append_dns_records(
        mac="00:50:56:aa:bb:cc",
        ip="10.10.10.5",
        hostname="host-a",
        domain="infra.plexplease.com",
        scope_network="10.10.10.0",
    )
    ptr = _rows(csv_path, rec_type="PTR")[0]
    assert ptr["name"] == "5.10.10.10.in-addr.arpa"
    assert ptr["parent"] == "10.10.10.in-addr.arpa"


def test_ptr_parent_zone_matches_dns_service(csv_path):
    """NetworkService must agree with DnsService, the canonical implementation."""
    from homelab_gitops.domain.dns import calculate_ptr

    svc = NetworkService(dns_csv_path=csv_path)
    svc.append_dns_records(
        mac="00:50:56:aa:bb:cc",
        ip="10.10.10.77",
        hostname="host-b",
        domain="infra.plexplease.com",
        scope_network="10.10.10.0",
    )
    ptr = _rows(csv_path, rec_type="PTR")[0]
    expected_zone, expected_domain = calculate_ptr("10.10.10.77")
    assert ptr["parent"] == expected_zone
    assert ptr["name"] == expected_domain


def test_batch_allocation_never_repeats_an_address(csv_path):
    """Consecutive allocations must differ even before anything is written."""
    svc = NetworkService(dns_csv_path=csv_path)
    with patch("homelab_gitops.domain.network.subprocess.run") as run:
        run.return_value.returncode = 1  # nothing answers: every address looks free
        allocated = [svc.get_next_ip("10.10.10.0") for _ in range(5)]
    assert "" not in allocated, "allocator ran out of addresses"
    assert len(set(allocated)) == 5, f"duplicate addresses handed out: {allocated}"


def test_allocation_skips_addresses_already_in_csv(csv_path):
    """Addresses recorded in the CSV are in use, whether or not they answer."""
    with open(csv_path, "a") as f:
        f.write("record,sw-core-01,infra.plexplease.com,A,10.10.10.2,3600,,,,,,,Dell switch,,\n")
        f.write("record,ap-01,infra.plexplease.com,A,10.10.10.3,3600,,,,,,,EnGenius AP,,\n")
    svc = NetworkService(dns_csv_path=csv_path)
    with patch("homelab_gitops.domain.network.subprocess.run") as run:
        run.return_value.returncode = 1  # silent: the old code would have taken these
        assert svc.get_next_ip("10.10.10.0") == "10.10.10.4"


def test_allocation_skips_hosts_that_answer(csv_path):
    """A responding address is in use even if it is absent from the CSV."""
    svc = NetworkService(dns_csv_path=csv_path)

    def fake_run(cmd, *a, **kw):
        class R:
            returncode = 0 if cmd[-1] in {"10.10.10.2", "10.10.10.3"} else 1

        return R()

    with patch("homelab_gitops.domain.network.subprocess.run", side_effect=fake_run):
        assert svc.get_next_ip("10.10.10.0") == "10.10.10.4"


def test_appended_record_is_excluded_from_later_allocation(csv_path):
    """Writing a record must remove that address from the free pool."""
    svc = NetworkService(dns_csv_path=csv_path)
    with patch("homelab_gitops.domain.network.subprocess.run") as run:
        run.return_value.returncode = 1
        first = svc.get_next_ip("10.10.10.0")
        svc.append_dns_records(
            mac="00:50:56:aa:bb:cc",
            ip=first,
            hostname="host-c",
            domain="infra.plexplease.com",
            scope_network="10.10.10.0",
        )
        second = NetworkService(dns_csv_path=csv_path).get_next_ip("10.10.10.0")
    assert second != first
