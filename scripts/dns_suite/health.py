import threading
import time
import subprocess
import re
import random
from datetime import datetime
from .core import DNS_SERVER, FW_SERVER, SSH_ADMIN_PASSWORD, init_db

class HealthMonitor(threading.Thread):
    def __init__(self, target_domains, run_id):
        super().__init__()
        self.targets = target_domains
        self.run_id = run_id
        self.daemon = True
        self.running = True
        self.stats = {
            "fw_states": 0,
            "dns_cpu_idle": 100.0,
            "dns_ram_avail_mb": 0,
            "ping_ms": 0.0,
            "cold_dns_ms": 0.0,
            "abort": False,
            "abort_reason": "",
            "phase": 0,
            "target_qps": 0,
            "actual_qps": 0.0
        }
        self.consecutive_network_failures = 0
        self.conn = init_db()

    def run(self):
        while self.running:
            try:
                # 1. Ping 1.1.1.1
                t0 = time.time()
                res = subprocess.run(["ping", "-c", "1", "-W", "1", "1.1.1.1"], stdout=subprocess.DEVNULL)
                if res.returncode == 0:
                    self.stats["ping_ms"] = (time.time() - t0) * 1000
                    self.consecutive_network_failures = 0
                else:
                    self.stats["ping_ms"] = -1
                    self.consecutive_network_failures += 1

                # 2. Cold DNS Lookup
                if self.targets:
                    d = random.choice(self.targets)
                    t0 = time.time()
                    subprocess.run(["dig", f"@{DNS_SERVER}", d, "+short", "+tries=1", "+timeout=2"], stdout=subprocess.DEVNULL)
                    self.stats["cold_dns_ms"] = (time.time() - t0) * 1000

                # 3. OPNsense FW States & DNS Resources via SSH
                if SSH_ADMIN_PASSWORD:
                    try:
                        fw_res = subprocess.run(
                            ["sshpass", "-p", SSH_ADMIN_PASSWORD, "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=2", f"root@{FW_SERVER}", "pfctl -si | grep 'current entries'"],
                            capture_output=True, text=True, timeout=3)
                        m = re.search(r'\d+', fw_res.stdout)
                        if m: self.stats["fw_states"] = int(m.group(0))
                    except: pass
                    
                    try:
                        dns_res = subprocess.run(
                            ["sshpass", "-p", SSH_ADMIN_PASSWORD, "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=2", f"ansible@{DNS_SERVER}", "top -b -n 1 | grep '%Cpu'; free -m | grep Mem"],
                            capture_output=True, text=True, timeout=3)
                        cpu_match = re.search(r'([\d\.]+)\s+id', dns_res.stdout)
                        if cpu_match: self.stats["dns_cpu_idle"] = float(cpu_match.group(1))
                        mem_lines = [l for l in dns_res.stdout.splitlines() if "Mem:" in l]
                        if mem_lines:
                            parts = mem_lines[0].split()
                            if len(parts) >= 7: self.stats["dns_ram_avail_mb"] = int(parts[6])
                    except: pass

                cursor = self.conn.cursor()
                cursor.execute('''INSERT INTO stresstest_metrics 
                    (run_id, phase, target_qps, actual_qps, fw_states, dns_cpu_idle, dns_ram_avail_mb, ping_ms, cold_dns_ms) 
                    VALUES (?,?,?,?,?,?,?,?,?)''',
                    (self.run_id, self.stats["phase"], self.stats["target_qps"], self.stats["actual_qps"], 
                     self.stats["fw_states"], self.stats["dns_cpu_idle"], self.stats["dns_ram_avail_mb"], 
                     self.stats["ping_ms"], self.stats["cold_dns_ms"]))
                self.conn.commit()

                # Safety Tripwires
                if self.stats["fw_states"] > 850000:
                    self.stats["abort"] = True; self.stats["abort_reason"] = f"Firewall States CRITICAL: {self.stats['fw_states']}"
                if 0 < self.stats["dns_ram_avail_mb"] < 300:
                    self.stats["abort"] = True; self.stats["abort_reason"] = f"DNS RAM CRITICAL: {self.stats['dns_ram_avail_mb']}MB avail"
                if self.consecutive_network_failures >= 3:
                    self.stats["abort"] = True; self.stats["abort_reason"] = "Network Ping CRITICAL: 3 consecutive timeouts"
                if self.stats["cold_dns_ms"] > 3000:
                    self.stats["abort"] = True; self.stats["abort_reason"] = f"Cold DNS Latency CRITICAL: {self.stats['cold_dns_ms']:.0f}ms"

            except Exception: pass
            time.sleep(2)
            
    def stop(self):
        self.running = False
        self.conn.close()
