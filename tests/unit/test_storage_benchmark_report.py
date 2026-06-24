# tests/unit/test_storage_benchmark_report.py
import json
import pytest
from pathlib import Path
from scripts.storage_benchmark_report import (
    parse_job_metrics,
    generate_summary_line,
    generate_markdown_table,
    assign_tiers,
)


def make_fio_job(name, read_iops=0, write_iops=0, read_bw_kb=0, read_lat_p99_ns=0, write_lat_p99_ns=0):
    return {
        "jobname": name,
        "read": {
            "iops": read_iops,
            "bw": read_bw_kb,
            "lat_ns": {"percentile": {"99.000000": read_lat_p99_ns}},
        },
        "write": {
            "iops": write_iops,
            "bw": 0,
            "lat_ns": {"percentile": {"99.000000": write_lat_p99_ns}},
        },
    }


def make_result(backend, protocol, phase, jobs):
    return {
        "backend": backend,
        "protocol": protocol,
        "phase": phase,
        "run_id": "2026-06-24T1430",
        "fio": {
            "jobs": jobs,
        },
    }


def test_parse_job_metrics_extracts_rand_read_iops():
    jobs = [
        make_fio_job("rand-read-4k", read_iops=145000),
        make_fio_job("rand-write-4k", write_iops=92000),
        make_fio_job("seq-read-1m", read_bw_kb=2150000),
        make_fio_job("mixed-7030-4k", read_lat_p99_ns=210000, write_lat_p99_ns=310000),
        make_fio_job("db-pattern-8k", read_lat_p99_ns=195000, write_lat_p99_ns=290000),
    ]
    result = make_result("nvme-local", "local", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["rand_read_iops"] == 145000


def test_parse_job_metrics_extracts_rand_write_iops():
    jobs = [
        make_fio_job("rand-read-4k", read_iops=12000),
        make_fio_job("rand-write-4k", write_iops=8000),
        make_fio_job("seq-read-1m", read_bw_kb=870000),
        make_fio_job("mixed-7030-4k", read_lat_p99_ns=1200000, write_lat_p99_ns=1800000),
        make_fio_job("db-pattern-8k", read_lat_p99_ns=980000, write_lat_p99_ns=1500000),
    ]
    result = make_result("K3S_HDD", "nfs4", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["rand_write_iops"] == 8000


def test_parse_job_metrics_converts_seq_read_to_mb():
    jobs = [
        make_fio_job("rand-read-4k"),
        make_fio_job("rand-write-4k"),
        make_fio_job("seq-read-1m", read_bw_kb=2150000),
        make_fio_job("mixed-7030-4k"),
        make_fio_job("db-pattern-8k"),
    ]
    result = make_result("nvme-local", "local", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["seq_read_mb"] == pytest.approx(2099.6, rel=0.01)


def test_parse_job_metrics_extracts_mixed_p99_us():
    jobs = [
        make_fio_job("rand-read-4k"),
        make_fio_job("rand-write-4k"),
        make_fio_job("seq-read-1m"),
        make_fio_job("mixed-7030-4k", read_lat_p99_ns=1200000, write_lat_p99_ns=1800000),
        make_fio_job("db-pattern-8k"),
    ]
    result = make_result("K3S_HDD", "nfs4", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["mixed_p99_us"] == pytest.approx(1500.0)  # avg of read+write


def test_parse_job_metrics_extracts_db_p99_us():
    jobs = [
        make_fio_job("rand-read-4k"),
        make_fio_job("rand-write-4k"),
        make_fio_job("seq-read-1m"),
        make_fio_job("mixed-7030-4k"),
        make_fio_job("db-pattern-8k", read_lat_p99_ns=980000, write_lat_p99_ns=1500000),
    ]
    result = make_result("K3S_HDD", "iscsi", "phase1", jobs)
    metrics = parse_job_metrics(result)
    assert metrics["db_p99_us"] == pytest.approx(1240.0)  # avg of read+write


def test_generate_summary_line_done():
    metrics = {
        "rand_read_iops": 12000,
        "rand_write_iops": 8000,
        "seq_read_mb": 870.0,
        "mixed_p99_us": 1500.0,
        "db_p99_us": 1240.0,
    }
    line = generate_summary_line("K3S_HDD", "nfs4", "phase1", metrics)
    assert "[DONE]" in line
    assert "K3S_HDD" in line
    assert "nfs4" in line
    assert "12000" in line
    assert "8000" in line


def test_generate_summary_line_pending():
    line = generate_summary_line("WHITEBOX", "iscsi", "phase1", None)
    assert "[WAIT]" in line
    assert "WHITEBOX" in line
    assert "pending" in line


def test_generate_markdown_table_has_headers():
    rows = [
        {
            "backend": "nvme-local", "protocol": "local", "phase": "phase1",
            "metrics": {"rand_read_iops": 145000, "rand_write_iops": 92000,
                        "seq_read_mb": 2100.0, "mixed_p99_us": 210.0, "db_p99_us": 195.0},
        },
        {
            "backend": "K3S_HDD", "protocol": "nfs4", "phase": "phase1",
            "metrics": None,
        },
    ]
    table = generate_markdown_table(rows)
    assert "| Backend |" in table
    assert "| Protocol |" in table
    assert "nvme-local" in table
    assert "145000" in table
    assert "K3S_HDD" in table
    assert "pending" in table


def test_assign_tiers_fast_is_best_db_p99():
    candidates = [
        {"backend": "nvme-local", "protocol": "local", "db_p99_us": 195.0, "rand_write_iops": 92000},
        {"backend": "K3S_HDD", "protocol": "iscsi", "db_p99_us": 980.0, "rand_write_iops": 45000},
        {"backend": "K3S_HDD", "protocol": "nfs4", "db_p99_us": 1240.0, "rand_write_iops": 8000},
    ]
    tiers = assign_tiers(candidates)
    assert tiers["fast"]["backend"] == "nvme-local"
    assert tiers["standard"]["backend"] == "K3S_HDD"
    assert tiers["bulk"]["backend"] == "K3S_HDD"
