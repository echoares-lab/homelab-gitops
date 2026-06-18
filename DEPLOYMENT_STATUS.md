# iSCSI Benchmark Deployment - Current Status

## ✅ Completed

### Benchmark Suite Implementation
- ✓ Complete iSCSI benchmarking framework implemented (`benchmarks/` directory)
- ✓ FIO workload profiles: database.fio, sequential.fio, mixed.fio
- ✓ SSH executor, metrics parser, configuration capturer
- ✓ Comparison engine and HTML report generator
- ✓ CLI orchestrator with comprehensive options

### Infrastructure Verification
- ✓ vCenter 10.10.10.9 accessible with administrator credentials
- ✓ ESXi host 10.10.10.11 accessible
- ✓ iSCSI_PRODUCTION datastore exists and is empty
- ✓ GOLDEN content library contains ubuntu-24.04-lts-golden OVF
- ✓ TrueNAS at 10.10.10.20 is accessible
- ✓ 1Password Connect integration working for credential retrieval

### Deployment Infrastructure
- ✓ OpenTofu/Terraform modules configured for VM provisioning
- ✓ Ansible playbooks ready for configuration
- ✓ All dependencies installed (pytest, paramiko, govc, etc.)

## ⚠️  Blocking Issue: OVF Deployment

### Problem
vCenter returns **HTTP 500 Internal Server Error** when attempting to deploy the OVF from the GOLDEN content library:

```
POST https://10.10.10.9/rest/com/vmware/vcenter/ovf/library-item/id:71aa0b55-8e2b-4179-88ba-d93dd9a3a487?~action=deploy: 500 Internal Server Error
```

**Tools tested:**
- ❌ Terraform/OpenTofu (`vsphere_virtual_machine` with `clone` block)
- ❌ govc `library.deploy` command
- ❌ Direct REST API calls

### Root Cause
The vCenter server is rejecting OVF deployment requests at the API level. This suggests either:
1. OVF deployment is not enabled/configured on this vCenter instance
2. The OVF library item is misconfigured
3. vCenter has insufficient resources/permissions
4. vCenter version incompatibility with the library item format

## ✅ Solutions (Choose One)

### Option A: Manual VM Creation via vCenter UI (Quickest)
1. Connect to vCenter at https://10.10.10.9
2. Right-click iSCSI_PRODUCTION datastore
3. Deploy OVF manually through GUI
4. Create 5 VMs: iscsi-bench-01 through iscsi-bench-05
5. Assign static IPs: 10.10.10.100 - 10.10.10.104

**Time estimate:** 15-20 minutes

### Option B: Clone Existing VM
Use govc to clone dev-01.mgmt.plexplease.com to iSCSI_PRODUCTION datastore:

```bash
for i in {01..05}; do
  govc vm.clone \
    -ds iSCSI_PRODUCTION \
    -host 10.10.10.11 \
    -vm /vm/Discovered\ virtual\ machine/dev-01.mgmt.plexplease.com \
    iscsi-bench-$i.mgmt.plexplease.com
done
```

**Pros:** Fully automated
**Cons:** VMs will have dev-01's OS configuration, not Ubuntu 24.04 LTS golden image

### Option C: Fix OVF Deployment (Advanced)
1. Check vCenter logs: `govc logs | grep -i ovf`
2. Verify OVF library item integrity in vCenter UI
3. Ensure "OVF Deployment" is enabled under vCenter Settings
4. Try uploading a fresh OVF to GOLDEN library
5. Contact vCenter support if issue persists

## 🚀 Next Steps

Once VMs are deployed (via any option above):

### 1. Verify SSH Access
```bash
for i in {100..104}; do
  ssh -o ConnectTimeout=5 ubuntu@10.10.10.$i "echo OK" && \
    echo "✓ 10.10.10.$i reachable"
done
```

### 2. Run Baseline Benchmark
```bash
python3 benchmarks/iscsi_benchmark.py \
  --profile database --vms 5 --label baseline \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104
```

### 3. Capture Baseline Config
```bash
python3 benchmarks/iscsi_benchmark.py \
  --capture-config --label baseline --truenas-host 10.10.10.20
```

### 4. Apply TrueNAS Optimizations
```bash
ssh root@10.10.10.20
zfs set recordsize=16K tank/iscsi_production_dataset
zfs set compression=lz4 tank/iscsi_production_dataset
zfs set primarycache=metadata tank/iscsi_production_dataset
echo "set zfs:zfs_arc_max = 34359738368" >> /etc/modprobe.d/zfs.conf
reboot
```

### 5. Run Optimized Benchmark
```bash
python3 benchmarks/iscsi_benchmark.py \
  --profile database --vms 5 --label optimized-v1 \
  --vm-ips 10.10.10.100 10.10.10.101 10.10.10.102 10.10.10.103 10.10.10.104
```

### 6. Generate Report
```bash
python3 benchmarks/iscsi_benchmark.py --compare baseline optimized-v1
open benchmarks/reports/comparison-*.html
```

## 📋 Deliverables Ready

- **iscsi_benchmark.py**: Complete CLI orchestrator
- **benchmarks/**: Full suite with SSH, metrics, reporting
- **Documentation**: BENCHMARK_QUICKSTART.md, REAL_VM_DEPLOYMENT_GUIDE.md
- **FIO Profiles**: database, sequential, mixed workloads
- **HTML Reports**: Professional comparison reports with metrics

All code is committed and ready for execution once VMs are available.

## 🔧 Recommendation

**Use Option A (Manual UI deployment)** if vCenter admin access available:
- Fastest path forward
- Most reliable (no API issues)
- Lets you configure VMs exactly as needed
- Takes ~20 minutes

**Use Option B (Clone)** if you want full automation:
- Scripted, repeatable
- But VMs won't have Ubuntu 24.04 golden image
- May still work for benchmarking purposes

---

**Status Summary:**
- Implementation: ✅ 100% Complete
- Infrastructure Setup: ⚠️ Blocked by vCenter OVF API (5-minute workaround via UI)
- Benchmarking: 🟢 Ready to run (waiting for VMs)
