# Real VM Deployment Guide: iSCSI Benchmark Testing

This guide walks you through deploying and benchmarking the iSCSI_PRODUCTION datastore using actual VMs in your homelab.

---

## Prerequisites Checklist

### Infrastructure Requirements
- [ ] ESXi host(s) with vCenter connectivity
- [ ] TrueNAS system at 10.10.10.20 with iSCSI_PRODUCTION target configured
- [ ] Network connectivity between your workstation and ESXi/TrueNAS
- [ ] Ubuntu 24.04 LTS golden image built and available in vCenter content library

### Credentials & Configuration
- [ ] vCenter credentials configured in environment or Terraform variables
- [ ] SSH key pair ready (~/.ssh/id_ed25519) for VM access
- [ ] TrueNAS API token (for config capture)
- [ ] OpenTofu installed and configured

### Software Requirements
```bash
# Install required tools
pip install -r requirements.txt          # Includes paramiko, jinja2
pip install ansible                      # For config management
terraform apply --version                # Verify Terraform/OpenTofu
govc version                             # vSphere CLI helper (optional)
fio --version                            # Verify FIO on benchmark VMs
```

---

## Step-by-Step Deployment

### Step 1: Prepare Golden Image (If Not Already Built)

```bash
# Build Ubuntu 24.04 LTS golden image with FIO pre-installed
python3 manage.py build ubuntu-2404

# Verify it's available in vCenter content library
govc library.vm.list /GOLDEN/ubuntu-24.04-lts-golden
```

**Expected Output:**
```
Name: ubuntu-24.04-lts-golden
Version: latest (or date-stamped)
Size: ~5GB
Status: READY
```

### Step 2: Configure Benchmark Profile

The profile has been updated to use iSCSI_PRODUCTION:

```yaml
# config/profiles/ubuntu-2404-iscsi-bench.yml
vcenter:
  datastore: "iSCSI_PRODUCTION"    # ← Now points to iSCSI instead of NFS
```

### Step 3: Deploy 5-10 Test VMs

Deploy between 5-10 VMs to simulate medium-scale concurrent load:

```bash
# Deploy VMs 01-05 (adjust count as needed)
for i in {01..05}; do
  echo "Deploying iscsi-bench-$i..."
  python3 manage.py deploy ubuntu-2404-iscsi-bench $i --host esxi-01.mgmt.plexplease.com
done

# Wait for all VMs to complete deployment (~10-15 min per VM)
# Monitor status
python3 manage.py status
```

**Expected Output:**
```
iscsi-bench-01.mgmt.plexplease.com  10.10.10.100  Running   Ubuntu 24.04
iscsi-bench-02.mgmt.plexplease.com  10.10.10.101  Running   Ubuntu 24.04
iscsi-bench-03.mgmt.plexplease.com  10.10.10.102  Running   Ubuntu 24.04
iscsi-bench-04.mgmt.plexplease.com  10.10.10.103  Running   Ubuntu 24.04
iscsi-bench-05.mgmt.plexplease.com  10.10.10.104  Running   Ubuntu 24.04
```

### Step 4: Verify VM Connectivity

Test SSH access to each VM:

```bash
# Test connectivity
for i in {100..104}; do
  ssh -o StrictHostKeyChecking=no ubuntu@10.10.10.$i "uname -a" && echo "✓ 10.10.10.$i OK" || echo "✗ 10.10.10.$i FAILED"
done

# Verify FIO is available
for i in {100..104}; do
  ssh -o StrictHostKeyChecking=no ubuntu@10.10.10.$i "fio --version" || echo "Installing FIO on 10.10.10.$i..."
done
```

### Step 5: Configure TrueNAS API Access

```bash
# Set TrueNAS API credentials
export TRUENAS_API_KEY="your-api-token-here"

# Test connectivity
curl -s -H "Authorization: Bearer $TRUENAS_API_KEY" \
  http://10.10.10.20/api/v2.0/pool | jq '.[0].name'
```

### Step 6: Capture Baseline Configuration

```bash
# Snapshot current system configuration
python3 benchmarks/iscsi_benchmark.py \
  --capture-config \
  --label baseline \
  --truenas-host 10.10.10.20

# Output: benchmarks/configs/2026-06-18-HHMMSS-baseline-config.json
```

### Step 7: Run Baseline Benchmarks

Run database workload benchmark across all VMs:

```bash
python3 benchmarks/iscsi_benchmark.py \
  --profile database \
  --vms 5 \
  --label baseline \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

# This runs for ~5 minutes (60 seconds × 5 VMs)
# Output: benchmarks/results/2026-06-18-HHMMSS-baseline-database.json
```

**Expected Output:**
```
INFO: Running database benchmark on 10.10.10.100
INFO: Running database benchmark on 10.10.10.101
...
INFO: Saved results to benchmarks/results/2026-06-18-100000-baseline-database.json

Sample Results:
- Total IOPS: ~4,500-5,000 (depends on TrueNAS performance)
- p99 Latency: ~8-15ms (depends on network/hardware)
- Throughput: ~20-30 MB/s
```

### Step 8: Apply Optimizations

Now apply the three optimization phases to your TrueNAS and ESXi:

#### Phase 1: TrueNAS ZFS Tuning

```bash
# SSH to TrueNAS
ssh root@10.10.10.20

# Optimize ZFS dataset for iSCSI workloads
zfs set recordsize=16K tank/iscsi_production_dataset
zfs set compression=lz4 tank/iscsi_production_dataset
zfs set primarycache=metadata tank/iscsi_production_dataset

# Increase ARC cache (adjust based on available RAM)
echo "set zfs:zfs_arc_max = 34359738368" >> /etc/modprobe.d/zfs.conf
reboot  # Required for ARC changes to take effect
```

#### Phase 2: iSCSI Target Tuning

```bash
# From TrueNAS UI or SSH:
# Navigate to: Sharing > Block Shares (iSCSI) > Global Configuration

# Set:
# - Max Connections Per Session: 128
# - NOPOUT Interval: 60
# - Login Timeout: 30 seconds
```

#### Phase 3: Network Optimization

```bash
# On TrueNAS:
# Enable Jumbo Frames (MTU 9000) on iSCSI network interface

# On ESXi:
# For each iSCSI network adapter:
# - MTU: 9000 (Jumbo Frames)
# - TCP Window Size: 512KB
# - Disable Nagle's Algorithm (if option available)
```

### Step 9: Verify Optimizations Applied

```bash
# Re-capture configuration after optimizations
python3 benchmarks/iscsi_benchmark.py \
  --capture-config \
  --label optimized-v1 \
  --truenas-host 10.10.10.20
```

### Step 10: Re-run Benchmarks on Optimized Infrastructure

```bash
# Wait ~1 hour after TrueNAS reboot for ARC to stabilize
sleep 3600

# Run same benchmark on optimized system
python3 benchmarks/iscsi_benchmark.py \
  --profile database \
  --vms 5 \
  --label optimized-v1 \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104

# Output: benchmarks/results/2026-06-18-110000-optimized-v1-database.json

# Expected Results:
# - Total IOPS: +20-35% improvement (6,000-7,500)
# - p99 Latency: -20-30% improvement (6-12ms)
# - Throughput: +20-35% improvement (30-45 MB/s)
```

### Step 11: Generate Comparison Report

```bash
# Compare baseline vs optimized
python3 benchmarks/iscsi_benchmark.py \
  --compare baseline optimized-v1

# This generates:
# - benchmarks/reports/comparison-2026-06-18-*.html (styled HTML report)
# - benchmarks/reports/metrics-2026-06-18-*.csv (Excel-ready CSV)
# - Console summary with improvements highlighted
```

---

## Expected Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| VM Deployment | 30-60 min | 5-10 min per VM |
| Baseline Testing | 10-15 min | 5 VMs × ~2 min each |
| Optimization Application | 30-60 min | Includes TrueNAS reboot |
| Optimization Verification | 10-15 min | Re-run benchmarks |
| Report Generation | 2-3 min | Automatic |
| **Total** | **2-3 hours** | Non-blocking reboot time |

---

## Monitoring During Testing

### Real-time Performance Monitoring

```bash
# On TrueNAS: Monitor ZFS I/O
arcstat 1  # Shows ARC hit ratio, misses
iostat -x 1  # Shows disk I/O
iotop  # Shows iSCSI process I/O

# On ESXi: Monitor iSCSI adapter performance
esxcli iscsi adapter stats get
esxcli storage core adapter list
```

### Log File Locations

```bash
# Benchmark logs
tail -f benchmarks/results/*.json

# TrueNAS syslog
ssh root@10.10.10.20 'tail -f /var/log/messages'

# ESXi logs
ssh root@esxi-01 'tail -f /var/log/vmkernel.log'
```

---

## Troubleshooting

### SSH Connection Issues

```bash
# If SSH fails, verify:
ssh -v -o ConnectTimeout=10 ubuntu@10.10.10.100

# Common issues:
# - SSH key permissions: chmod 600 ~/.ssh/id_ed25519
# - Host not yet booted: wait 2-3 minutes after deploy completes
# - Network isolation: verify iSCSI VLAN connectivity
```

### FIO Not Found on VMs

```bash
# Install FIO on benchmark VMs
for i in {100..104}; do
  ssh ubuntu@10.10.10.$i 'sudo apt-get update && sudo apt-get install -y fio'
done
```

### TrueNAS API Access Denied

```bash
# Verify API token is valid
curl -s -H "Authorization: Bearer $TRUENAS_API_KEY" \
  http://10.10.10.20/api/v2.0/auth/me | jq .

# If invalid, regenerate token from TrueNAS UI:
# System → Advanced → API Keys
```

### Low Performance After Optimization

```bash
# Verify optimizations actually applied:
zfs get recordsize,compression tank/iscsi_production_dataset
arc_summary  # Check ARC cache settings

# If settings reverted, TrueNAS may have rebooted
# Re-apply and add to persistent config (/etc/modprobe.d/)
```

---

## Advanced: Running All Three Workload Profiles

```bash
# Run comprehensive benchmark suite
for profile in database sequential mixed; do
  echo "Testing $profile workload..."
  python3 benchmarks/iscsi_benchmark.py \
    --profile $profile \
    --vms 5 \
    --label baseline \
    --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104
  
  sleep 60  # Cool down between tests
done

# Generate separate reports for each
for profile in database sequential mixed; do
  python3 benchmarks/iscsi_benchmark.py \
    --compare baseline optimized-v1
done
```

---

## Data Preservation & Analysis

```bash
# Archive results for historical comparison
mkdir -p benchmarks/archives/$(date +%Y-%m-%d)
cp benchmarks/results/*.json benchmarks/archives/$(date +%Y-%m-%d)/
cp benchmarks/reports/*.html benchmarks/archives/$(date +%Y-%m-%d)/

# Track metrics over time
git add benchmarks/OPTIMIZATION_REPORT.md
git commit -m "perf: iSCSI optimization results for $(date +%Y-%m-%d)"
```

---

## Success Criteria

You've successfully completed real VM testing when:

✅ All 5-10 VMs deployed and reachable via SSH  
✅ Baseline captured and benchmarks complete (5-15 min)  
✅ Optimizations applied (ZFS, iSCSI, network)  
✅ Optimized benchmarks complete  
✅ Comparison report generated  
✅ IOPS improved by +20-30% (or more)  
✅ Latency improved by -20-30% (or more)  

---

## Next Steps After Testing

1. **Review Results**
   - Open `benchmarks/reports/comparison-*.html` in browser
   - Share HTML report with infrastructure team

2. **Make Production Decision**
   - If improvements meet requirements: schedule production deployment
   - If not: implement Tier 1 optimizations (SPDK, more ARC, etc.)

3. **Monitor Production**
   - Deploy optimizations to production iSCSI_PRODUCTION
   - Monitor for 48 hours to ensure stability
   - Update documentation with final settings

4. **Plan Future Optimization**
   - Review `benchmarks/OPTIMIZATION_REPORT.md` Tier 1 & 2 recommendations
   - Schedule SPDK or advanced tuning if needed

---

## Questions?

For issues or questions:
- Check `benchmarks/README.md` for CLI reference
- Review `benchmarks/OPTIMIZATION_REPORT.md` for technical details
- Check logs in `benchmarks/results/` and `benchmarks/reports/` directories
