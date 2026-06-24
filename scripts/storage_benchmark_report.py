#!/usr/bin/env python3
"""Storage benchmark report generator.

Reads per-backend fio JSON results and produces:
  - report-live.md  (updated after each backend — interim)
  - report-final.md (full comparison + tier recommendations)
  - summary.txt     (one-liner per backend for `watch`)
"""
import argparse
import json
from pathlib import Path
from typing import Optional


ALL_BACKENDS = [
    ("nvme-local", "local", "phase1"),
    ("nvme-local", "local", "phase2"),
    ("K3S_HDD", "nfs4", "phase1"),
    ("K3S_HDD", "nfs4", "phase2"),
    ("vmstore", "nfs4", "phase1"),
    ("vmstore", "nfs4", "phase2"),
    ("WHITEBOX", "nfs4", "phase1"),
    ("WHITEBOX", "nfs4", "phase2"),
    ("K3S_HDD", "iscsi", "phase1"),
    ("K3S_HDD", "iscsi", "phase2"),
    ("vmstore", "iscsi", "phase1"),
    ("vmstore", "iscsi", "phase2"),
    ("WHITEBOX", "iscsi", "phase1"),
    ("WHITEBOX", "iscsi", "phase2"),
]


def parse_job_metrics(result: dict) -> dict:
    """Extract key performance metrics from a fio result dict."""
    jobs = {j["jobname"]: j for j in result["fio"]["jobs"]}

    def lat_avg_us(job_name: str) -> float:
        j = jobs.get(job_name, {})
        r_ns = j.get("read", {}).get("lat_ns", {}).get("percentile", {}).get("99.000000", 0)
        w_ns = j.get("write", {}).get("lat_ns", {}).get("percentile", {}).get("99.000000", 0)
        return ((r_ns + w_ns) / 2) / 1000

    return {
        "rand_read_iops": int(jobs.get("rand-read-4k", {}).get("read", {}).get("iops", 0)),
        "rand_write_iops": int(jobs.get("rand-write-4k", {}).get("write", {}).get("iops", 0)),
        "seq_read_mb": jobs.get("seq-read-1m", {}).get("read", {}).get("bw", 0) / 1024,
        "mixed_p99_us": lat_avg_us("mixed-7030-4k"),
        "db_p99_us": lat_avg_us("db-pattern-8k"),
    }


def generate_summary_line(backend: str, protocol: str, phase: str, metrics: Optional[dict]) -> str:
    """Return a one-liner status string for summary.txt."""
    label = f"{backend} {protocol} {phase}"
    if metrics is None:
        return f"[WAIT] {label:<40} pending"
    return (
        f"[DONE] {label:<40} "
        f"r={metrics['rand_read_iops']:>6} w={metrics['rand_write_iops']:>6} iops | "
        f"seq={metrics['seq_read_mb']:>6.0f}MB/s | "
        f"p99={metrics['mixed_p99_us']:>7.0f}µs | "
        f"db_p99={metrics['db_p99_us']:>7.0f}µs"
    )


def generate_markdown_table(rows: list) -> str:
    """Render results as a GitHub-flavoured markdown table."""
    header = (
        "| Backend | Protocol | Phase | Rand R IOPS | Rand W IOPS | "
        "Seq R MB/s | Mixed p99 µs | DB p99 µs |\n"
        "|---------|----------|-------|-------------|-------------|"
        "-----------|-------------|----------|\n"
    )
    lines = [header]
    for row in rows:
        m = row.get("metrics")
        if m:
            lines.append(
                f"| {row['backend']} | {row['protocol']} | {row['phase']} | "
                f"{m['rand_read_iops']} | {m['rand_write_iops']} | "
                f"{m['seq_read_mb']:.0f} | {m['mixed_p99_us']:.0f} | {m['db_p99_us']:.0f} |\n"
            )
        else:
            lines.append(
                f"| {row['backend']} | {row['protocol']} | {row['phase']} | "
                "pending | pending | pending | pending | pending |\n"
            )
    return "".join(lines)


def assign_tiers(candidates: list) -> dict:
    """Assign fast/standard/bulk tiers from phase1 results.

    fast    = lowest db_p99_us (best for stateful DBs)
    standard = second-lowest db_p99_us
    bulk    = remaining (highest capacity assumption)
    """
    sorted_by_db = sorted(candidates, key=lambda c: c["db_p99_us"])
    fast = sorted_by_db[0] if len(sorted_by_db) > 0 else {}
    standard = sorted_by_db[1] if len(sorted_by_db) > 1 else {}
    bulk = sorted_by_db[2] if len(sorted_by_db) > 2 else sorted_by_db[-1] if sorted_by_db else {}
    return {"fast": fast, "standard": standard, "bulk": bulk}


def run_report(run_dir: Path, mode: str) -> None:
    result_files = sorted(run_dir.glob("*-phase*.json"))
    loaded = {}
    for f in result_files:
        try:
            data = json.loads(f.read_text())
            key = f.stem
            loaded[key] = data
        except (json.JSONDecodeError, KeyError):
            continue

    rows = []
    summary_lines = []
    for backend, protocol, phase in ALL_BACKENDS:
        key = f"{backend}-{protocol}-{phase}"
        result = loaded.get(key)
        metrics = parse_job_metrics(result) if result else None
        rows.append({"backend": backend, "protocol": protocol, "phase": phase, "metrics": metrics})
        summary_lines.append(generate_summary_line(backend, protocol, phase, metrics))

    table = generate_markdown_table(rows)

    live_path = run_dir / "report-live.md"
    live_path.write_text(f"# Storage Benchmark — Live Results\n\n{table}\n")

    summary_path = run_dir / "summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n")

    if mode == "final":
        phase1_metrics = [
            {**{"backend": r["backend"], "protocol": r["protocol"]}, **r["metrics"]}
            for r in rows
            if r["phase"] == "phase1" and r["metrics"] is not None
        ]
        tiers = assign_tiers(phase1_metrics)

        tier_section = (
            "\n## Tier Recommendations\n\n"
            f"| Tier | StorageClass | Backend | Protocol | DB p99 µs |\n"
            f"|------|-------------|---------|----------|-----------|\n"
            f"| Fast | storage-fast | {tiers.get('fast', {}).get('backend', 'TBD')} | "
            f"{tiers.get('fast', {}).get('protocol', 'TBD')} | "
            f"{tiers.get('fast', {}).get('db_p99_us', 'N/A')} |\n"
            f"| Standard | storage-standard | {tiers.get('standard', {}).get('backend', 'TBD')} | "
            f"{tiers.get('standard', {}).get('protocol', 'TBD')} | "
            f"{tiers.get('standard', {}).get('db_p99_us', 'N/A')} |\n"
            f"| Bulk | storage-bulk | {tiers.get('bulk', {}).get('backend', 'TBD')} | "
            f"{tiers.get('bulk', {}).get('protocol', 'TBD')} | "
            f"{tiers.get('bulk', {}).get('db_p99_us', 'N/A')} |\n"
        )

        final_path = run_dir / "report-final.md"
        final_path.write_text(f"# Storage Benchmark — Final Results\n\n{table}{tier_section}\n")
        print(f"Final report written to {final_path}")
        print(tier_section)

    print("\n".join(summary_lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Storage benchmark report generator")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=["interim", "final"], default="interim")
    args = parser.parse_args()
    run_report(args.run_dir, args.mode)


if __name__ == "__main__":
    main()
