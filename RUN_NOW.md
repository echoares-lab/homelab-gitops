# Execute iSCSI Benchmark Now - Step by Step

## ✅ Confirmed Prerequisites

- ✓ Golden image exists: `ubuntu-24.04-lts-golden` (5.34 GB, OVF Template)
- ✓ Location: GOLDEN content library
- ✓ ESXi: 10.10.10.11 accessible
- ✓ iSCSI_PRODUCTION datastore configured
- ✓ TrueNAS: 10.10.10.20

---

## 🚀 Execute Now

### Step 1: Configure vCenter Credentials (Your Machine)

```bash
# Set environment variables (replace with your actual credentials)
export VSPHERE_USER="administrator@vsphere.local"
export VSPHERE_PASSWORD="your-vcenter-password"
export VSPHERE_SERVER="vcenter.mgmt.plexplease.com"  # or IP address
export VSPHERE_ALLOW_UNVERIFIED_SSL=true

# Verify credentials work
terraform init tofu/
```

### Step 2: Deploy 5 Benchmark VMs (10-15 minutes)

```bash
# Deploy VMs 01-05 sequentially to iSCSI_PRODUCTION
for i in {01..05}; do
  echo "=== Deploying iscsi-bench-$i ==="
  python3 manage.py deploy ubuntu-2404-iscsi-bench $i --host 10.10.10.11
  echo "Waiting 30 seconds before next deployment..."
  sleep 30
done

# Verify all VMs deployed successfully
python3 manage.py status
```

**Expected output:** 5 VMs running on iSCSI_PRODUCTION datastore
- iscsi-bench-01.mgmt.plexplease.com → 10.10.10.100
- iscsi-bench-02.mgmt.plexplease.com → 10.10.10.101
- iscsi-bench-03.mgmt.plexplease.com → 10.10.10.102
- iscsi-bench-04.mgmt.plexplease.com → 10.10.10.103
- iscsi-bench-05.mgmt.plexplease.com → 10.10.10.104

### Step 3: Verify SSH Connectivity (5 minutes)

```bash
# Test SSH access to each VM
for i in {100..104}; do
  echo "Testing 10.10.10.$i..."
  ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ubuntu@10.10.10.$i "echo OK" && \
    echo "✓ 10.10.10.$i reachable" || \
    echo "✗ 10.10.10.$i unreachable"
done

# Install FIO on all VMs if needed
for i in {100..104}; do
  ssh -o StrictHostKeyChecking=no ubuntu@10.10.10.$i "which fio >/dev/null || sudo apt-get update && sudo apt-get install -y fio"
done
```

### Step 4: Capture BASELINE Configuration (1 minute)

```bash
python3 benchmarks/iscsi_benchmark.py \
  --capture-config --label baseline --truenas-host 10.10.10.20

echo "✓ Baseline config captured"
```

### Step 5: Run BASELINE Benchmark (5 minutes)

```bash
echo "Starting baseline database workload benchmark..."
python3 benchmarks/iscsi_benchmark.py \
  --profile database --vms 5 --label baseline \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

echo "✓ Baseline benchmark complete"
ls -lh benchmarks/results/
```

### Step 6: Review Baseline Results (1 minute)

```bash
# View baseline metrics
cat benchmarks/results/*baseline-database.json | jq '.results[0].metrics | keys'

# Sample output (individual VM metrics):
cat benchmarks/results/*baseline-database.json | jq '.results[0].metrics'
```

---

## 🔧 Apply Optimizations (60+ minutes including reboot)

### Phase 1: TrueNAS ZFS Tuning

```bash
# SSH to TrueNAS
ssh root@10.10.10.20

# ====== EXECUTE ON TRUENAS ======

# Optimize ZFS recordsize for 4KB I/O
zfs set recordsize=16K tank/iscsi_production_dataset

# Enable compression
zfs set compression=lz4 tank/iscsi_production_dataset

# Optimize cache
zfs set primarycache=metadata tank/iscsi_production_dataset

# Increase ARC (Adaptive Replacement Cache) - adjust 34GB based on available RAM
echo "set zfs:zfs_arc_max = 34359738368" >> /etc/modprobe.d/zfs.conf

# CRITICAL: Reboot to apply ARC changes
reboot

# ====== END TRUENAS COMMANDS ======

# Wait for reboot (usually 2-3 minutes)
# Then wait 1 hour for ARC to stabilize

echo "Waiting 1 hour for TrueNAS ARC to stabilize..."
sleep 3600
```

### Phase 2 & 3: iSCSI and Network (Optional - For Advanced Users)

Skip these for now and test with Phase 1 optimizations first.

---

## 📊 Run OPTIMIZED Benchmark (5 minutes)

```bash
echo "Starting optimized database workload benchmark..."

# Capture optimized configuration
python3 benchmarks/iscsi_benchmark.py \
  --capture-config --label optimized-v1 --truenas-host 10.10.10.20

# Run optimized benchmark
python3 benchmarks/iscsi_benchmark.py \
  --profile database --vms 5 --label optimized-v1 \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

echo "✓ Optimized benchmark complete"
```

### View Optimized Results

```bash
# View optimized metrics
cat benchmarks/results/*optimized-v1-database.json | jq '.results[0].metrics'
```

---

## 📈 Generate Comparison Report (1 minute)

```bash
# Generate comparison
python3 benchmarks/iscsi_benchmark.py --compare baseline optimized-v1

# View report
open benchmarks/reports/comparison-*.html  # macOS
xdg-open benchmarks/reports/comparison-*.html  # Linux
```

**Report includes:**
- Side-by-side metrics comparison
- Improvement percentages for each metric
- Color-coded results (green = improvement, red = regression)
- Professional HTML formatting

---

## 📋 Expected Results

### Baseline (Before Optimization)
```
IOPS:        4,500-5,500
p99 Latency: 8-15ms
Throughput:  20-30 MB/s
```

### Optimized (After TrueNAS Tuning)
```
IOPS:        6,000-7,500  (+30-40%)
p99 Latency: 6-10ms       (-30-40%)
Throughput:  30-45 MB/s   (+30-40%)
```

---

## 🧹 Clean Up (When Done)

```bash
# Destroy test VMs
for i in {01..05}; do
  echo "Destroying iscsi-bench-$i..."
  python3 manage.py destroy iscsi-bench-$i.mgmt.plexplease.com
done

# Verify cleanup
python3 manage.py status
```

---

## ⏱️ Total Time Estimate

| Phase | Time | Notes |
|-------|------|-------|
| VM Deployment | 15 min | 5 VMs × 3 min each |
| Baseline Benchmark | 5 min | 60 sec × 5 VMs |
| TrueNAS Optimization | 60 min | Includes reboot + stabilization |
| Optimized Benchmark | 5 min | 60 sec × 5 VMs |
| Report Generation | 1 min | Automatic |
| **TOTAL** | **~90 min** | Mostly waiting for reboot |

---

## ✅ Success Checklist

After completing all steps:
- [ ] 5 VMs deployed to iSCSI_PRODUCTION
- [ ] SSH access verified to all VMs
- [ ] Baseline benchmark complete (~5,000 IOPS)
- [ ] TrueNAS optimization applied
- [ ] Optimized benchmark complete (~6,500+ IOPS)
- [ ] Comparison report generated
- [ ] Results show +30-40% improvement
- [ ] HTML report generated and reviewed

---

## 🆘 Troubleshooting

### VMs not deploying
```bash
# Check vCenter credentials
echo $VSPHERE_USER
echo $VSPHERE_SERVER

# Verify golden image exists
# vCenter UI → Content Libraries → GOLDEN → ubuntu-24.04-lts-golden
```

### SSH connection failed
```bash
# Verify VMs are actually running
python3 manage.py status

# Check network connectivity
ping 10.10.10.100

# Verify SSH key permissions
chmod 600 ~/.ssh/id_ed25519

# Try manual SSH with verbose output
ssh -vvv -o StrictHostKeyChecking=no ubuntu@10.10.10.100
```

### Benchmark fails with "FIO not found"
```bash
# Install FIO manually
ssh ubuntu@10.10.10.100 'sudo apt-get install -y fio'

# Verify FIO installed
ssh ubuntu@10.10.10.100 'fio --version'
```

### Low performance results
```bash
# Verify TrueNAS optimization was applied
ssh root@10.10.10.20 'zfs get recordsize,compression tank/iscsi_production_dataset'

# Verify ARC increased
ssh root@10.10.10.20 'arc_summary | head -20'
```

---

## 📚 Documentation Reference

- **CLI Commands:** `benchmarks/README.md`
- **Detailed Deployment:** `benchmarks/REAL_VM_DEPLOYMENT_GUIDE.md`
- **Technical Analysis:** `benchmarks/OPTIMIZATION_REPORT.md`
- **Quick Ref:** This file

---

**You're ready! Execute Step 1 and follow through. Report back with results!** 🚀
