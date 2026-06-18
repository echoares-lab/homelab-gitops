# iSCSI Datastore Performance Testing & Optimization Design

**Date:** 2026-06-18  
**Scope:** Baseline performance testing of iSCSI_PRODUCTION datastore (TrueNAS 10.10.10.20 → ESXi 10.10.10.11)  
**Focus Metrics:** IOPS and latency  
**Workload Scale:** Medium (5-10 concurrent VMs)  
**Optimization Priority:** TrueNAS-first, then ESXi and network tuning

---

## Problem Statement

The new iSCSI_PRODUCTION datastore needs comprehensive performance testing and optimization to support multiple concurrent VMs. Currently, there is no baseline measurement or optimization data. The objective is to:

1. Establish a performance baseline (IOPS, latency, throughput)
2. Identify bottlenecks across TrueNAS, ESXi, and network layers
3. Optimize iteratively and measure improvements
4. Support mixed workload patterns (database, sequential, general-purpose)

---

## Architecture

### High-Level Design

The solution uses a **hybrid approach** combining two independent systems:

1. **VM Provisioning** — Existing `manage.py` orchestrator
   - Provisions 5-10 test VMs using `ubuntu-2404-iscsi-bench.yml` profile
   - VMs remain running across multiple benchmark cycles
   - Eliminates provisioning overhead during optimization iterations

2. **Benchmark Suite** — New standalone tool in `benchmarks/` folder
   - Orchestrates FIO workloads on test VMs via SSH
   - Measures IOPS, latency (p50/p95/p99), and throughput
   - Stores results as timestamped JSON snapshots
   - Generates comparison reports showing baseline vs. optimized performance

### Separation of Concerns

- **Orchestrator** (`manage.py`) — Handles VM lifecycle
- **Benchmark tool** (`benchmarks/iscsi_benchmark.py`) — Handles performance measurement
- **Workloads** (`benchmarks/workloads/`) — FIO configurations for different workload patterns
- **Results** (`benchmarks/results/`) — Timestamped JSON snapshots with metadata
- **Reports** (`benchmarks/reports/`) — Comparison analysis and trends

---

## Workflow

### Phase 1: Baseline Establishment

1. Provision test VMs (one-time):
   ```bash
   python3 manage.py deploy ubuntu-2404-iscsi-bench 01 --host esxi-01.mgmt.plexplease.com
   python3 manage.py deploy ubuntu-2404-iscsi-bench 02 --host esxi-01.mgmt.plexplease.com
   # ... repeat for 5-10 VMs
   ```

2. Capture current TrueNAS/ESXi configuration:
   ```bash
   python3 scripts/iscsi_benchmark.py --capture-config --label baseline
   ```

3. Run baseline benchmarks across all workload profiles:
   ```bash
   python3 scripts/iscsi_benchmark.py --profile database --vms 5 --label baseline
   python3 scripts/iscsi_benchmark.py --profile sequential --vms 5 --label baseline
   python3 scripts/iscsi_benchmark.py --profile mixed --vms 5 --label baseline
   ```

4. Output: Timestamped JSON files in `benchmarks/results/`

### Phase 2: Optimize & Re-test (Iterative)

1. Apply optimization (e.g., TrueNAS recordsize tuning, caching policy change)
2. Capture new config snapshot
3. Re-run same benchmark suite
4. Compare against baseline:
   ```bash
   python3 scripts/iscsi_benchmark.py --compare baseline optimized-v1
   ```
5. Review results (IOPS improvement, latency reduction, regressions)
6. Decide next optimization or declare complete

### Optimization Sequence

- **Round 1:** TrueNAS optimizations (recordsize, compression, caching, iSCSI target tuning)
- **Round 2:** ESXi optimizations (VMFS blocksize, multipath policies, queue depth)
- **Round 3:** Network optimizations (MTU, iSCSI settings)

---

## Benchmark Workloads

### Workload Profiles

| Workload | I/O Pattern | Block Size | Read/Write Ratio | Use Case | Duration |
|----------|-------------|------------|------------------|----------|----------|
| **Database** | Random | 4KB | 70/30 | OLTP, high-IOPS scenarios | 60s |
| **Sequential** | Sequential | 128KB | 50/50 | Backups, bulk transfers | 60s |
| **Mixed** | Random + Sequential | Mixed | 50/50 | General-purpose workloads | 60s |

### Concurrency Model

- **Per VM:** 4-8 concurrent FIO jobs
- **Total:** 5-10 VMs × 4-8 jobs = 20-80 parallel I/O operations
- **Rationale:** Simulates medium-scale production environment with multiple VM workloads

### Metrics Captured

**IOPS Metrics:**
- Overall IOPS
- Read IOPS
- Write IOPS

**Latency Metrics (milliseconds):**
- p50 (median)
- p95 (95th percentile)
- p99 (99th percentile)
- p100 (worst-case)

**Throughput Metrics:**
- MB/s (overall)
- MB/s read
- MB/s write

**Variance:**
- Standard deviation
- Jitter detection

---

## Success Criteria & Targets

### Baseline Phase
- **Success:** Capture baseline IOPS and latency for all three workload patterns
- **No numerical targets yet** — baseline establishes current state

### Optimization Phases
- **IOPS target:** +20-30% improvement after TrueNAS tuning
- **Latency target:** Sub-5ms p99 latency for database workload (post-all-optimization)
- **Throughput:** No regression >10% (roll back any optimization causing this)
- **Stability:** Repeated runs show <5% variance in IOPS/latency

---

## Directory Structure

```
benchmarks/
├── iscsi_benchmark.py          # Main benchmark orchestrator (SSH, FIO execution, parsing, comparison)
├── workloads/
│   ├── database.fio            # 4KB random reads (70%) + writes (30%)
│   ├── sequential.fio          # 128KB sequential reads/writes
│   └── mixed.fio               # Mixed pattern for general workloads
├── results/
│   ├── 2026-06-18-baseline-database.json
│   ├── 2026-06-18-baseline-sequential.json
│   ├── 2026-06-18-baseline-mixed.json
│   ├── 2026-06-18-optimized-v1-database.json
│   └── ...                     # Timestamped results from each run
├── reports/
│   ├── comparison-2026-06-18.html    # HTML report comparing baseline vs. optimized
│   └── metrics-summary.csv           # CSV summary for charting
└── configs/
    ├── baseline-config.json    # TrueNAS + ESXi settings snapshot
    ├── optimized-v1-config.json
    └── ...
```

---

## Implementation Strategy

### Core Components

1. **Benchmark Tool** (`iscsi_benchmark.py`)
   - FIO orchestrator: Generates workload profiles, executes on test VMs
   - SSH executor: Connects to VMs, transfers FIO config, captures output
   - Metrics parser: Extracts IOPS, latency, throughput from FIO JSON
   - Config capturer: Snapshots TrueNAS/ESXi settings before each run
   - Comparison engine: Diffs results, highlights improvements and regressions
   - Report generator: Creates HTML and CSV summaries

2. **Workload Files** (FIO format)
   - Each workload file defines jobs, block sizes, read/write ratios, duration
   - Parameterizable: can adjust concurrency, duration, target

3. **Result Storage** (JSON)
   - Schema includes: timestamp, workload type, metric values, TrueNAS config snapshot, ESXi config snapshot
   - Enables historical tracking and trend analysis

### Technology Stack

- **FIO** — Industry-standard I/O benchmark tool (generates workloads, captures metrics)
- **Python 3** — Orchestration, SSH, parsing, reporting
- **Paramiko/SSH** — Remote execution on test VMs
- **JSON** — Result storage and comparison
- **HTML/CSV** — Report generation

---

## Testing Strategy

### Baseline Validation

- Run each workload 2-3 times to verify consistency
- Results should show <5% variance between runs (indicates stable environment)
- If variance >5%, investigate system noise before proceeding

### Optimization Validation

- After each optimization, run full benchmark suite once
- Compare against baseline using comparison engine
- If improvement detected, run again to verify repeatability
- If regression detected, evaluate trade-offs or roll back

### Edge Cases & Error Handling

- **VM unreachable:** Tool reports SSH connection error, skips VM, continues with others
- **FIO not installed:** Tool detects, suggests installation via manage.py config
- **Datastore full during test:** Tool monitors available space, warns if dropping below 10%
- **Test timeout:** Set 5-minute timeout per workload, fail gracefully with partial results

---

## Success Metrics for Implementation

After implementation, this design is successful if:

1. ✅ Benchmark tool can provision/run on 5-10 VMs concurrently
2. ✅ Results are reproducible (same config = <5% variance)
3. ✅ Captures baseline IOPS and p99 latency for database workload
4. ✅ Comparison reports clearly show improvements/regressions
5. ✅ Can complete full benchmark suite in <10 minutes
6. ✅ Results stored and tracked over multiple optimization rounds

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Slow benchmark execution | Limits optimization cycles | Parallelize FIO jobs, run tests in parallel across VMs |
| VM crashes during test | Incomplete data | Monitor VM health, add retry logic for failed jobs |
| FIO not available in golden image | Setup friction | Include FIO in ubuntu-2404-iscsi-bench build or install via Ansible |
| Results too noisy (high variance) | Unreliable comparisons | Run multiple times, identify and isolate system noise sources |
| Optimization causes workload regression | Production risk | Strict rollback policy: >10% throughput drop = automatic rollback |

---

## Future Enhancements

- Real-time visualization dashboard (live IOPS/latency graphs)
- Automated optimization recommendations based on bottleneck detection
- Integration with Grafana/Prometheus for historical trending
- Support for workload replays (record and replay production I/O patterns)

---

## Approval

- **Design Date:** 2026-06-18
- **Reviewed By:** [awaiting user approval]
- **Status:** [awaiting implementation plan]
