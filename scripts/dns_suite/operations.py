import os
import sys
import time
import re
import statistics
import random
import subprocess
import threading
import sqlite3
import asyncio
import dns.message
import dns.asyncquery
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from .core import (
    DOMAIN_FILE, DNS_SERVER, DB_PATH, 
    init_db, api_call, get_cache_full_crawl,
    acquire_lock, release_lock, log_progress, get_percentile
)
from .health import HealthMonitor

def sync_popularity(mock: bool = False):
    """Sync volatile Technitium hit counters into persistent SQLite memory."""
    print("[blue]Syncing popularity data from Technitium to SQLite...[/blue]")
    _, records = get_cache_full_crawl(mock=mock)
    
    conn = init_db()
    cursor = conn.cursor()
    
    updated = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for r in records:
        domain = r.get("full_name")
        hits = int(r.get("hits", 0))
        if hits > 0:
            cursor.execute('''
                INSERT INTO domain_popularity (domain, total_hits, last_seen, first_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    total_hits = total_hits + excluded.total_hits,
                    last_seen = excluded.last_seen
            ''', (domain, hits, now, now))
            updated += 1
            
    conn.commit()
    conn.close()
    print(f"[green]✓ Persistent popularity synced for {updated:,} domains.[/green]")

def run_analysis(mock: bool = False, run_id: int = None, console=None):
    if console: console.rule("Cache Impact Analysis")
    else: print("\n--- Cache Impact Analysis ---")
    
    unique_domains, records = get_cache_full_crawl(mock=mock)
    ttls = []
    for r in records:
        m = re.match(r"^(\d+)", str(r.get("ttl")))
        if m: ttls.append(int(m.group(1)))
    
    if not ttls:
        print("Cache is empty.")
        return
    
    avg_ttl = statistics.mean(ttls)
    median_ttl = statistics.median(ttls)

    if console:
        from rich.panel import Panel
        console.print(Panel(f"Unique Records: {len(ttls):,}\nAverage TTL: {avg_ttl:,.1f}s\nMedian TTL: {median_ttl:,.1f}s", title="Cache Status", border_style="blue"))
    else:
        print(f"Records: {len(ttls):,}\nAvg TTL: {avg_ttl:,.1f}s\nMedian TTL: {median_ttl:,.1f}s")

    min_ttl_vals = [0, 5, 10, 30, 60, 120, 300, 1800, 3600] 
    elig_vals = [0, 30, 60, 300]
    
    if run_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO analysis_stats (run_id, unique_records, avg_ttl, median_ttl) VALUES (?, ?, ?, ?)',
                       (run_id, len(ttls), avg_ttl, median_ttl))
    
    table = None
    if console:
        from rich.table import Table
        from rich import box
        table = Table(title="Maintenance QPS Impact Matrix", box=box.DOUBLE_EDGE)
        table.add_column("Min TTL", style="cyan")
        for e in elig_vals: table.add_column(f"Elig {e}s", justify="right")
    
    for m in min_ttl_vals:
        row = [f"{m}s"]
        for e in elig_vals:
            qps = sum(1.0 / max(t, m, 1) for t in ttls if max(t, m, 1) >= e)
            row.append(f"{qps:,.4f}")
            if run_id:
                cursor.execute('INSERT INTO qps_impact (run_id, min_ttl, eligibility, qps) VALUES (?, ?, ?, ?)', (run_id, m, e, qps))
        if table: table.add_row(*row)
    
    if table: console.print(table)
    if run_id:
        conn.commit()
        conn.close()

def _prefill_internal(count: int, qps: int, threads: int, mock: bool = False, randomize: bool = False, console=None):
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO runs (run_type, is_mock) VALUES (?, ?)', ('prefill_analysis', int(mock)))
    run_id = cursor.lastrowid
    conn.commit()

    msg = f"Starting Incremental Prefill: {count:,} domains @ {qps} QPS"
    if console:
        from rich.panel import Panel
        console.print(Panel(msg, border_style="green"))
    else: print(msg)

    print("[INIT] Scanning existing cache (Step 1/3)...")
    cached_domains, _ = get_cache_full_crawl(mock=mock)
    print(f"[INIT] Found {len(cached_domains):,} domains already in cache.")

    if mock: all_pool = [f"domain-{i}.com" for i in range(count + 5000)]
    else:
        if not os.path.exists(DOMAIN_FILE):
            print(f"Error: {DOMAIN_FILE} not found.")
            return
        with open(DOMAIN_FILE, 'r') as f:
            all_pool = [line.strip() for line in f if line.strip()]
            if randomize: 
                print("[INIT] Randomizing pool (Step 2/3)...")
                random.shuffle(all_pool)
    
    targets = [d for d in all_pool if d not in cached_domains][:count]

    if not targets:
        print("✓ All requested domains are already cached.")
        cursor.execute('UPDATE runs SET status = "completed" WHERE id = ?', (run_id,))
        conn.commit()
        run_analysis(mock=mock, run_id=run_id, console=console)
        return

    print(f"[EXEC] Targeting {len(targets):,} new domains (Step 3/3)...")
    interval = 1.0 / qps
    start_time = time.time()
    latencies = []
    
    lock = threading.Lock()
    active_futures = []

    def lookup(domain):
        t0 = time.time()
        success = False
        if mock:
            time.sleep(random.uniform(0.01, 0.05))
            dt = time.time() - t0
            success = True
        else:
            try:
                subprocess.run(["dig", f"@{DNS_SERVER}", domain, "+short", "+tries=1", "+timeout=2"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                dt = time.time() - t0
                success = True
            except:
                dt = 0
        
        if success:
            with lock:
                latencies.append(dt)
        return dt

    is_atty = sys.stdout.isatty()
    progress = None
    task = None
    
    try:
        if console and is_atty:
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
            progress = Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), 
                          TextColumn("[progress.percentage]{task.percentage:>3.1f}%"), TimeRemainingColumn(), 
                          console=console)
            progress.start()
            task = progress.add_task(f"Prefilling {len(targets):,}", total=len(targets))
            
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for i, domain in enumerate(targets):
                target_start = start_time + (i * interval)
                now = time.time()
                if now < target_start: time.sleep(target_start - now)
                
                f = executor.submit(lookup, domain)
                active_futures.append(f)
                
                if progress: progress.update(task, advance=1)
                
                if (i + 1) % 1000 == 0 or (i + 1) == len(targets):
                    pct = (i + 1) / len(targets) * 100
                    with lock:
                        avg_lat = statistics.mean(latencies) * 1000.0 if latencies else 0
                        log_progress(run_id, pct, i+1, len(targets), avg_lat, len(active_futures))
                    if not is_atty:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatched: {i+1}/{len(targets)} ({pct:.1f}%) | Avg Latency: {avg_lat:.1f}ms")

            print("\n[FINISH] All queries dispatched. Finalizing results...")
            for f in as_completed(active_futures):
                pass
                
        cursor.execute('UPDATE runs SET status = "completed" WHERE id = ?', (run_id,))
        conn.commit()

    except KeyboardInterrupt:
        print("\n[CANCEL] Prefill cancelled by user.")
        cursor.execute('UPDATE runs SET status = "cancelled" WHERE id = ?', (run_id,))
        conn.commit()
        if progress: progress.stop()
        return

    if progress: progress.stop()

    if latencies:
        ms = [l * 1000.0 for l in latencies]
        stats = {"Avg": statistics.mean(ms), "P1": get_percentile(ms, 1), "P5": get_percentile(ms, 5), "P25": get_percentile(ms, 25),
                 "P50": get_percentile(ms, 50), "P75": get_percentile(ms, 75), "P95": get_percentile(ms, 95), "P99": get_percentile(ms, 99)}
        
        if console:
            from rich.table import Table
            from rich import box
            pt = Table(title="Latency Distribution", box=box.SIMPLE_HEAD)
            pt.add_column("Metric"); pt.add_column("ms", justify="right")
            for k, v in stats.items(): pt.add_row(k, f"{v:,.2f}")
            console.print(pt)
        
        print("[FINAL] Refreshing cache snapshot for metrics...")
        _, all_records = get_cache_full_crawl(mock=mock)
        final_size = len(all_records)
        cursor.execute('INSERT INTO prefill_metrics (run_id, count, qps_limit, avg_ms, p1_ms, p5_ms, p25_ms, p50_ms, p75_ms, p95_ms, p99_ms, final_cache_size) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (run_id, len(targets), qps, stats["Avg"], stats["P1"], stats["P5"], stats["P25"], stats["P50"], stats["P75"], stats["P95"], stats["P99"], final_size))
        conn.commit()
    
    conn.close()
    run_analysis(mock=mock, run_id=run_id, console=console)

def prefill(count: int, qps: int, threads: int, mock: bool = False, randomize: bool = False, console=None):
    acquire_lock()
    try:
        _prefill_internal(count, qps, threads, mock, randomize, console)
    finally:
        release_lock()

# --- ASYNCIO STRESS TEST ---

async def async_lookup(domain: str, mock: bool) -> float:
    t0 = time.time()
    if mock:
        await asyncio.sleep(random.uniform(0.01, 0.05))
        return time.time() - t0
    q = dns.message.make_query(domain, "A")
    try:
        await dns.asyncquery.udp(q, DNS_SERVER, timeout=2.0)
        return time.time() - t0
    except:
        return 0.0

async def run_stresstest(targets: List[str], run_id: int, phases: List[tuple], mock: bool, console=None):
    print("\n[INIT] Increasing Technitium Cache Size to 2,000,000...")
    if not mock:
        res = api_call("settings/set", {"cacheMaximumEntries": 2000000})
        if res.get("status") == "ok":
            print("✓ Increased Cache Size to 2M successfully.")
        else:
            print(f"✗ Failed to increase cache size: {res.get('errorMessage')}")

    monitor = HealthMonitor(targets[:5000], run_id)
    monitor.start()

    latencies = []
    total_processed = 0
    phase_idx = 0
    start_time = time.time()
    phase_start_time = start_time
    
    active_tasks = set()
    interval = 1.0 / phases[0][0]
    monitor.stats["phase"] = 1
    monitor.stats["target_qps"] = phases[0][0]

    last_qps_calc = time.time()
    qps_count = 0

    print("\n[EXEC] Beginning Phased Live Stress Test...")
    print("---------------------------------------------------------------------------------------------")
    print(f"{'Time':<10} | {'Phase':<5} | {'Tgt QPS':<7} | {'Act QPS':<7} | {'States':<7} | {'CPU%':<5} | {'RAM Av':<8} | {'Ping ms':<7} | {'Cold ms':<7}")
    print("---------------------------------------------------------------------------------------------")

    last_print = time.time()

    for i, domain in enumerate(targets):
        if monitor.stats["abort"]:
            print(f"\n[ABORT TRIGGERED] {monitor.stats['abort_reason']}")
            break

        now = time.time()
        
        # Check if we need to advance phase
        if now - phase_start_time > phases[phase_idx][1]:
            phase_idx += 1
            if phase_idx >= len(phases):
                print("\n[FINISH] All test phases completed successfully!")
                break
            
            phase_start_time = now
            interval = 1.0 / phases[phase_idx][0]
            monitor.stats["phase"] = phase_idx + 1
            monitor.stats["target_qps"] = phases[phase_idx][0]
            print(f"\n>>>>> ENTERING PHASE {phase_idx + 1} | Target QPS: {phases[phase_idx][0]} <<<<<\n")

        # Pacing
        target_start = phase_start_time + (qps_count * interval)
        if now < target_start:
            await asyncio.sleep(target_start - now)

        # Dispatch
        task = asyncio.create_task(async_lookup(domain, mock))
        active_tasks.add(task)
        
        def task_done(t):
            active_tasks.discard(t)
            res = t.result()
            if res > 0: latencies.append(res)
            
        task.add_done_callback(task_done)
        qps_count += 1
        total_processed += 1
        
        # Calculate Actual QPS
        if now - last_qps_calc >= 2.0:
            monitor.stats["actual_qps"] = qps_count / (now - last_qps_calc)
            qps_count = 0
            last_qps_calc = now
            
        # Logging progress for the generic monitor
        if total_processed % 5000 == 0:
            log_progress(run_id, (total_processed/len(targets))*100, total_processed, len(targets), statistics.mean(latencies)*1000 if latencies else 0, len(active_tasks))

        if now - last_print >= 5.0:
            last_print = now
            print(f"{datetime.now().strftime('%H:%M:%S'):<10} | {monitor.stats['phase']:<5} | {monitor.stats['target_qps']:<7} | {monitor.stats['actual_qps']:<7.1f} | {monitor.stats['fw_states']:<7} | {100-monitor.stats['dns_cpu_idle']:<5.1f} | {monitor.stats['dns_ram_avail_mb']:<6}MB | {monitor.stats['ping_ms']:<7.1f} | {monitor.stats['cold_dns_ms']:<7.1f}")

    monitor.stop()
    
    if active_tasks:
        print("[FINISH] Waiting for straggler queries to resolve...")
        await asyncio.gather(*active_tasks, return_exceptions=True)
        
    return latencies, monitor.stats["abort"], monitor.stats["abort_reason"]

def stresstest(count: int, phases: List[tuple], mock: bool = False, console=None):
    acquire_lock()
    try:
        conn = init_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO runs (run_type, is_mock) VALUES (?, ?)', ('stresstest', int(mock)))
        run_id = cursor.lastrowid
        conn.commit()

        print("\n[INIT] Scanning cache for missing domains...")
        cached_domains, _ = get_cache_full_crawl(mock=mock)
        
        if mock:
            all_pool = [f"domain-{i}.com" for i in range(count + 5000)]
        else:
            if not os.path.exists(DOMAIN_FILE):
                print(f"Error: {DOMAIN_FILE} not found.")
                return

            with open(DOMAIN_FILE, 'r') as f:
                all_pool = [line.strip() for line in f if line.strip()]
                random.shuffle(all_pool)
            
        targets = [d for d in all_pool if d not in cached_domains][:count]
        print(f"[INIT] Prepared {len(targets):,} targets for Stress Test.")
        
        latencies, aborted, reason = asyncio.run(run_stresstest(targets, run_id, phases, mock, console))
        
        if aborted:
            cursor.execute('UPDATE runs SET status = ? WHERE id = ?', (f"aborted: {reason}", run_id))
        else:
            cursor.execute('UPDATE runs SET status = "completed" WHERE id = ?', (run_id,))
        conn.commit()
        
        if latencies:
            ms = [l * 1000.0 for l in latencies]
            print("\n--- Stress Test Latency Results ---")
            print(f"  Avg: {statistics.mean(ms):.2f}ms")
            print(f"  P1:  {get_percentile(ms, 1):.2f}ms")
            print(f"  P5:  {get_percentile(ms, 5):.2f}ms")
            print(f"  P25: {get_percentile(ms, 25):.2f}ms")
            print(f"  P50: {get_percentile(ms, 50):.2f}ms")
            print(f"  P75: {get_percentile(ms, 75):.2f}ms")
            print(f"  P95: {get_percentile(ms, 95):.2f}ms")
            print(f"  P99: {get_percentile(ms, 99):.2f}ms")

        conn.close()
    finally:
        release_lock()

# --- OTHER COMMANDS ---

def monitor_progress():
    conn = init_db(); cursor = conn.cursor()
    cursor.execute('SELECT id, status FROM runs WHERE run_type = "prefill_analysis" ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    if not row: print("No prefill runs found."); return
    
    run_id, status = row
    print(f"Monitoring Run ID: {run_id} | Status: {status} (Ctrl+C to stop)")
    
    last_processed = 0
    stalls = 0
    try:
        while True:
            cursor.execute('SELECT percent, processed, total, avg_ms, timestamp, queue_size FROM progress_logs WHERE run_id = ? ORDER BY timestamp DESC LIMIT 1', (run_id,))
            p = cursor.fetchone()
            if p:
                if p[1] == last_processed: stalls += 1
                else: stalls = 0
                warn = " [RETRYING/STALLED?]" if stalls > 5 else ""
                print(f"\r[{p[4]}] {p[0]:.1f}% ({p[1]}/{p[2]}) | Latency: {p[3]:.1f}ms | Queue: {p[5]}{warn}   ", end="")
                last_processed = p[1]
                if p[0] >= 100 and status == "completed":
                    print("\nRun completed.")
                    break
            else:
                print("\rWaiting for first progress entry...", end="")
            
            cursor.execute('SELECT status FROM runs WHERE id = ?', (run_id,))
            res = cursor.fetchone()
            if res:
                status = res[0]
                if status != "running":
                    print(f"\nRun status changed to: {status}")
                    break
            time.sleep(5)
    except KeyboardInterrupt: print("\nMonitoring stopped.")
    conn.close()

def view_history(console=None):
    conn = init_db(); cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, run_type, status FROM runs ORDER BY id DESC LIMIT 15')
    runs = cursor.fetchall()
    if console:
        from rich.table import Table
        from rich import box
        table = Table(title="Historical Runs", box=box.ROUNDED)
        table.add_column("ID", style="dim"); table.add_column("Time"); table.add_column("Type", style="cyan"); table.add_column("Status")
        for r in runs: table.add_row(str(r[0]), r[1], r[2], r[3])
        console.print(table)
    else:
        for r in runs: print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
    conn.close()
