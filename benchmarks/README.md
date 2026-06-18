# iSCSI Datastore Benchmark Suite

Performance testing and optimization toolkit for iSCSI_PRODUCTION datastore on TrueNAS → ESXi.

## Quick Start

### 1. Provision Test VMs (One-Time)

```bash
# Create 5-10 test VMs using existing profile
python3 manage.py deploy ubuntu-2404-iscsi-bench 01 --host esxi-01.mgmt.plexplease.com
python3 manage.py deploy ubuntu-2404-iscsi-bench 02 --host esxi-01.mgmt.plexplease.com
# ... repeat for 5-10 VMs
```

### 2. Capture Baseline Configuration

```bash
python3 benchmarks/iscsi_benchmark.py --capture-config --label baseline
```

### 3. Run Baseline Benchmarks

```bash
python3 benchmarks/iscsi_benchmark.py --profile database --vms 5 --label baseline
python3 benchmarks/iscsi_benchmark.py --profile sequential --vms 5 --label baseline
python3 benchmarks/iscsi_benchmark.py --profile mixed --vms 5 --label baseline
```

### 4. Compare Results

After optimization, run again with different label:

```bash
python3 benchmarks/iscsi_benchmark.py --profile database --vms 5 --label optimized-v1

# Compare baseline vs optimized
python3 benchmarks/iscsi_benchmark.py --compare baseline optimized-v1
```

Reports are generated in `benchmarks/reports/`.

## CLI Reference

```
python3 benchmarks/iscsi_benchmark.py [OPTIONS]

Options:
  --profile {database,sequential,mixed}
    Workload profile to run
  
  --vms NUM
    Number of test VMs (default: 5)
  
  --label TEXT
    Label for this run (baseline, optimized-v1, etc.)
  
  --vm-ips IP [IP ...]
    Specific VM IP addresses to benchmark
  
  --capture-config
    Capture system configuration snapshot
  
  --compare BASELINE OPTIMIZED
    Compare two benchmark runs by label
  
  --truenas-host IP
    TrueNAS host IP (default: 10.10.10.20)
```

## Workload Profiles

### Database (database.fio)
- **Pattern:** 4KB random
- **Read/Write:** 70% reads, 30% writes
- **Use Case:** OLTP, high-IOPS database workloads

### Sequential (sequential.fio)
- **Pattern:** 128KB sequential
- **Read/Write:** 50% reads, 50% writes
- **Use Case:** Backups, bulk data transfer

### Mixed (mixed.fio)
- **Pattern:** Random (4KB) + Sequential (128KB)
- **Read/Write:** 50/50
- **Use Case:** General-purpose workloads

## Output Structure

```
benchmarks/
├── results/
│   ├── 2026-06-18-101000-baseline-database.json
│   ├── 2026-06-18-101500-baseline-sequential.json
│   └── ...
├── reports/
│   ├── comparison-2026-06-18-101530.html
│   └── metrics-2026-06-18-101530.csv
└── configs/
    ├── 2026-06-18-101000-baseline-config.json
    └── ...
```

### Results Format

Each JSON result file contains:
```json
{
  "timestamp": "2026-06-18-101000",
  "profile": "database",
  "label": "baseline",
  "results": [
    {
      "vm_ip": "10.10.10.100",
      "profile": "database",
      "label": "baseline",
      "metrics": {
        "total_iops": 5000,
        "read_iops": 3500,
        "write_iops": 1500,
        "read_lat_p99_ms": 10.0,
        ...
      }
    }
  ]
}
```

## Troubleshooting

### SSH Connection Errors
- Verify VM SSH key at `~/.ssh/id_ed25519`
- Check VMs are on network and pingable
- Verify ubuntu user exists on test VMs

### FIO Not Available
- FIO must be installed on test VMs:
  ```bash
  sudo apt-get update && sudo apt-get install -y fio
  ```
- Or add to ansible playbook for benchmark role

### High Variance in Results
- Ensure no other workloads on ESXi host
- Warm up disks with 5-minute pre-run
- Run 2-3 times and average results

## Success Criteria

✅ Baseline established for all 3 workload profiles
✅ IOPS measurements < 5% variance between runs
✅ Latency p99 captured for database workload
✅ Comparison reports clearly show improvements/regressions
✅ Full benchmark suite completes in < 10 minutes

## References

- [FIO Documentation](https://fio.readthedocs.io/)
- [TrueNAS API Docs](https://www.truenas.com/api-docs/)
- [ESXi Performance Tuning](https://core.vmware.com/esxi-best-practices)
