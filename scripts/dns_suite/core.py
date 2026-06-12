import os
import sqlite3
import requests
import re
import random
import sys
import threading
from typing import List, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
TECHNITIUM_URL = os.environ.get("TECHNITIUM_HOST", "http://127.0.0.1:5380")
TECHNITIUM_TOKEN = os.environ.get("TECHNITIUM_TOKEN", "")
if os.path.exists("config/.env.local"):
    with open("config/.env.local") as f:
        for line in f:
            if line.startswith("TECHNITIUM_TOKEN="):
                TECHNITIUM_TOKEN = line.strip().split("=", 1)[1]
            elif line.startswith("TECHNITIUM_HOST="):
                TECHNITIUM_URL = line.strip().split("=", 1)[1]

SSH_ADMIN_PASSWORD = os.environ.get("SSH_ADMIN_PASSWORD", "")
DOMAIN_FILE = "config/top_10m_domains.txt"
DNS_SERVER = "10.10.10.2"
FW_SERVER = "10.10.10.1"
RESULTS_DIR = "results"
DB_PATH = os.path.join(RESULTS_DIR, "dns_suite.db")
LOCK_FILE = os.path.join(RESULTS_DIR, "dns_suite.lock")

# --- UTILS ---

def format_safe(val: float, precision: int = 2) -> str:
    s = f"{val:.{precision}f}"
    if "." in s:
        p0, p1 = s.split(".")
        return f"{'_'.join(p0)} . {'_'.join(p1)}"
    return "_".join(s)

def get_percentile(data: List[float], p: float) -> float:
    if not data: return 0.0
    data_sorted = sorted(data)
    idx = int(len(data_sorted) * (p / 100.0))
    return data_sorted[min(idx, len(data_sorted)-1)]

# --- DATABASE ---

def init_db():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP, 
        run_type TEXT, 
        is_mock INTEGER,
        status TEXT DEFAULT 'running')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS domain_popularity (
        domain TEXT PRIMARY KEY,
        total_hits INTEGER DEFAULT 0,
        last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
        first_seen TEXT DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS progress_logs (
        run_id INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, 
        percent REAL, processed INTEGER, total INTEGER, avg_ms REAL,
        queue_size INTEGER DEFAULT 0, FOREIGN KEY(run_id) REFERENCES runs(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stresstest_metrics (
        run_id INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, phase INTEGER,
        target_qps INTEGER, actual_qps REAL, fw_states INTEGER, dns_cpu_idle REAL,
        dns_ram_avail_mb INTEGER, ping_ms REAL, cold_dns_ms REAL, FOREIGN KEY(run_id) REFERENCES runs(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS prefill_metrics (
        run_id INTEGER, count INTEGER, qps_limit INTEGER, avg_ms REAL, p1_ms REAL, p5_ms REAL, p25_ms REAL, 
        p50_ms REAL, p75_ms REAL, p95_ms REAL, p99_ms REAL, final_cache_size INTEGER, FOREIGN KEY(run_id) REFERENCES runs(id))''')
    cursor.execute('CREATE TABLE IF NOT EXISTS analysis_stats (run_id INTEGER, unique_records INTEGER, avg_ttl REAL, median_ttl REAL, FOREIGN KEY(run_id) REFERENCES runs(id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS qps_impact (run_id INTEGER, min_ttl INTEGER, eligibility INTEGER, qps REAL, FOREIGN KEY(run_id) REFERENCES runs(id))')
    conn.commit()
    return conn

def log_progress(run_id: int, percent: float, processed: int, total: int, avg_ms: float, queue_size: int = 0):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO progress_logs (run_id, percent, processed, total, avg_ms, queue_size) VALUES (?, ?, ?, ?, ?, ?)',
                       (run_id, percent, processed, total, avg_ms, queue_size))
        conn.commit()
        conn.close()
    except: pass

# --- LOCKING ---

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r') as f:
            try:
                pid = f.read().strip()
                if pid and os.path.exists(f"/proc/{pid}"):
                    print(f"Error: Another instance is running (PID: {pid}).")
                    sys.exit(1)
            except: pass
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

def release_lock():
    if os.path.exists(LOCK_FILE):
        try: os.remove(LOCK_FILE)
        except: pass

# --- API ---

def api_call(endpoint: str, params: dict = None, mock: bool = False) -> dict:
    if mock:
        if "cache/list" in endpoint:
            return {"status": "ok", "response": {"records": [{"name": f"mock{i}", "ttl": f"{random.randint(1, 3600)}", "hits": random.randint(0, 10)} for i in range(50)], "zones": ["mock.com"]}}
        return {"status": "ok"}
    if not TECHNITIUM_TOKEN:
        return {"status": "error", "errorMessage": "TECHNITIUM_TOKEN environment variable not set."}
    if params is None: params = {}
    params["token"] = TECHNITIUM_TOKEN
    try:
        response = requests.get(f"{TECHNITIUM_URL}/api/{endpoint}", params=params, timeout=30)
        return response.json()
    except Exception as e:
        return {"status": "error", "errorMessage": str(e)}

def get_cache_full_crawl(mock: bool = False) -> Tuple[Set[str], List[Dict]]:
    unique_domains = set()
    all_records = []
    lock = threading.Lock()

    def process_zone(domain: str):
        data = api_call("cache/list", {"domain": domain}, mock=mock).get("response", {})
        for r in data.get("records", []):
            name = r.get("name")
            full = f"{name}.{domain}".strip(".") if name else domain
            if full:
                with lock:
                    if full not in unique_domains:
                        unique_domains.add(full)
                        r["full_name"] = full
                        all_records.append(r)
        return data.get("zones", [])

    root_zones = process_zone("")
    if not root_zones: return unique_domains, all_records

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_zone, zone): zone for zone in root_zones}
        for future in as_completed(futures): pass
    return unique_domains, all_records
