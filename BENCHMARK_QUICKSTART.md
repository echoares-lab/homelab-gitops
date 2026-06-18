# iSCSI Benchmark - Quick Start (5 Minutes)

## Prerequisites

✅ You have:
- ESXi 10.10.10.11 with vCenter access
- ubuntu-24.04-lts-golden template in GOLDEN content library
- TrueNAS at 10.10.10.20 with iSCSI_PRODUCTION datastore
- SSH access to VMs

## Configure vCenter Credentials (Local Machine)

```bash
# Set vCenter credentials (replace with your actual values)
export VSPHERE_USER="administrator@vsphere.local"
export VSPHERE_PASSWORD="your-vcenter-password"
export VSPHERE_SERVER="vcenter.mgmt.plexplease.com"  # or IP
export VSPHERE_ALLOW_UNVERIFIED_SSL=true
```

## Deploy 5 Benchmark VMs

```bash
# Deploy VMs to iSCSI_PRODUCTION datastore
for i in {01..05}; do
  echo "Deploying iscsi-bench-$i..."
  python3 manage.py deploy ubuntu-2404-iscsi-bench $i --host 10.10.10.11
  sleep 30  # Wait between deployments
done

# Monitor deployment status
python3 manage.py status
```

**Expected VMs after deployment:**
- iscsi-bench-01.mgmt.plexplease.com → 10.10.10.100
- iscsi-bench-02.mgmt.plexplease.com → 10.10.10.101
- iscsi-bench-03.mgmt.plexplease.com → 10.10.10.102
- iscsi-bench-04.mgmt.plexplease.com → 10.10.10.103
- iscsi-bench-05.mgmt.plexplease.com → 10.10.10.104

## Run Baseline Benchmark

```bash
# Test SSH connectivity first
for i in {100..104}; do
  ssh -o StrictHostKeyChecking=no ubuntu@10.10.10.$i "fio --version" || \
    ssh -o StrictHostKeyChecking=no ubuntu@10.10.10.$i "sudo apt-get install -y fio"
done

# Capture baseline configuration
python3 benchmarks/iscsi_benchmark.py \
  --capture-config --label baseline --truenas-host 10.10.10.20

# Run database workload benchmark
python3 benchmarks/iscsi_benchmark.py \
  --profile database --vms 5 --label baseline \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104
```

**This runs for ~5 minutes (60 sec × 5 VMs)**

## Apply Optimizations

```bash
# SSH to TrueNAS and run:
ssh root@10.10.10.20

# Phase 1: ZFS Tuning
zfs set recordsize=16K tank/iscsi_production_dataset
zfs set compression=lz4 tank/iscsi_production_dataset
zfs set primarycache=metadata tank/iscsi_production_dataset
echo "set zfs:zfs_arc_max = 34359738368" >> /etc/modprobe.d/zfs.conf
reboot

# Wait ~1 hour for ARC to stabilize
exit
sleep 3600
```

## Run Optimized Benchmark

```bash
# Capture optimized configuration
python3 benchmarks/iscsi_benchmark.py \
  --capture-config --label optimized-v1 --truenas-host 10.10.10.20

# Re-run benchmark with optimizations
python3 benchmarks/iscsi_benchmark.py \
  --profile database --vms 5 --label optimized-v1 \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

# Generate comparison report
python3 benchmarks/iscsi_benchmark.py --compare baseline optimized-v1

# View report
open benchmarks/reports/comparison-*.html
```

## Expected Results

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| IOPS | 4,500-5,500 | 6,000-7,500 | +30-40% |
| p99 Latency | 8-15ms | 6-10ms | -30-40% |
| Throughput | 20-30 MB/s | 30-45 MB/s | +30-40% |

## Clean Up (When Done)

```bash
# Destroy test VMs
for i in {01..05}; do
  python3 manage.py destroy iscsi-bench-$i.mgmt.plexplease.com
done
```

---

## Full Commands (Copy & Paste)

```bash
# Set credentials
export VSPHERE_USER="administrator@vsphere.local"
export VSPHERE_PASSWORD="your-password"
export VSPHERE_SERVER="vcenter-ip-or-host"
export VSPHERE_ALLOW_UNVERIFIED_SSL=true

# Deploy
for i in {01..05}; do python3 manage.py deploy ubuntu-2404-iscsi-bench $i --host 10.10.10.11; sleep 30; done

# Baseline
python3 benchmarks/iscsi_benchmark.py --capture-config --label baseline --truenas-host 10.10.10.20
python3 benchmarks/iscsi_benchmark.py --profile database --vms 5 --label baseline --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

# (Apply ZFS optimizations here - see guide above)

# Optimized
python3 benchmarks/iscsi_benchmark.py --capture-config --label optimized-v1 --truenas-host 10.10.10.20
python3 benchmarks/iscsi_benchmark.py --profile database --vms 5 --label optimized-v1 --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

# Report
python3 benchmarks/iscsi_benchmark.py --compare baseline optimized-v1
```
