#!/usr/bin/env python3
import os
import requests
import subprocess
import time
import re
import random
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from typing import List, Set, Dict

# Configuration
TECHNITIUM_URL = os.environ.get("TECHNITIUM_HOST", "http://127.0.0.1:5380")
TECHNITIUM_TOKEN = os.environ.get("TECHNITIUM_TOKEN", "")
DNS_SERVER = "127.0.0.1"
DB_PATH = "results/dns_suite.db"

# Smart Budgeting
MAX_QPS = float(os.environ.get("HEARTBEAT_QPS", "350.0"))
QPS_WINDOW_SIZE = 10 # Seconds to average QPS over
query_history = deque()

def api_call(endpoint: str, params: dict = None) -> dict:
    if params is None: params = {}
    params["token"] = TECHNITIUM_TOKEN
    try:
        response = requests.get(f"{TECHNITIUM_URL}/api/{endpoint}", params=params, timeout=15)
        return response.json().get("response", {})
    except:
        return {}

def parse_ttl(ttl_str: str) -> int:
    match = re.match(r"^(\d+)", str(ttl_str))
    return int(match.group(1)) if match else 0

def get_weighted_targets() -> List[str]:
    """
    Predictive Analytics Engine:
    Prioritizes domains based on 30-day SQLite hit counts.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fetch Top 100,000 domains by popularity in last 30 days
        cursor.execute('''
            SELECT domain FROM domain_popularity 
            WHERE last_seen > datetime('now', '-30 days')
            ORDER BY total_hits DESC LIMIT 100000
        ''')
        popular_domains = {r[0] for r in cursor.fetchall()}
        conn.close()
    except:
        popular_domains = set()

    targets = []
    
    def process_zone(domain: str):
        data = api_call("cache/list", {"domain": domain})
        for r in data.get("records", []):
            ttl = parse_ttl(r.get("ttl"))
            if ttl < 60:
                name = r.get("name")
                full = f"{name}.{domain}".strip(".") if name else domain
                if not full: continue
                
                # Check if it's in our predictive "VIP" list
                if full in popular_domains:
                    # Give it a small chance to be skipped to spread load
                    targets.append(full)
        return data.get("zones", [])

    # Parallel TLD scan for the heartbeat
    root_zones = process_zone("")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_zone, zone): zone for zone in root_zones}
        for future in as_completed(futures): pass
            
    return targets

def check_budget() -> bool:
    now = time.time()
    while query_history and query_history[0] < (now - QPS_WINDOW_SIZE):
        query_history.popleft()
    current_qps = len(query_history) / QPS_WINDOW_SIZE
    return current_qps < MAX_QPS

def refresh_domain(domain: str):
    query_history.append(time.time())
    try:
        subprocess.run(
            ["dig", f"@{DNS_SERVER}", domain, "+short", "+timeout=1"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except: pass

def main():
    print(f"[{time.ctime()}] Starting Predictive 30-Day Heartbeat (Budget: {MAX_QPS} QPS)...")
    
    while True:
        try:
            # 1. Fetch Priority Targets (Winners)
            targets = get_weighted_targets()
            print(f"[{time.ctime()}] Weighted scan complete. {len(targets)} VIP domains ready.")

            if not targets:
                # If no VIPs yet, fall back to current hit-based logic
                print(f"[{time.ctime()}] No predictive data yet. Waiting for sync...")
                time.sleep(60)
                continue

            # 2. Steady refresh within budget
            random.shuffle(targets)
            for d in targets:
                if check_budget():
                    refresh_domain(d)
                    time.sleep(1.0 / MAX_QPS)
                else:
                    time.sleep(0.1) # Back off
            
            print(f"[{time.ctime()}] Cycle finished. Sleeping 30s...")
            time.sleep(30)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
