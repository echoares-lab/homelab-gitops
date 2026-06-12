import argparse
import sys
import sqlite3
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .core import init_db, api_call, DB_PATH
from .operations import prefill, run_analysis, stresstest, monitor_progress, view_history, sync_popularity

console = Console()

def interactive_stresstest():
    console.print(Panel("[bold yellow]Interactive Live Stress Test Setup[/bold yellow]"))
    count = int(Prompt.ask("Target Domain Count", default="500000"))
    start_qps = int(Prompt.ask("Starting QPS", default="250"))
    step_qps = int(Prompt.ask("QPS Step Increase", default="100"))
    duration = int(Prompt.ask("Phase Duration (seconds)", default="60"))
    max_qps = int(Prompt.ask("Max QPS Limit", default="1000"))
    
    phases = []
    current_qps = start_qps
    while current_qps <= max_qps:
        phases.append((current_qps, duration))
        current_qps += step_qps
        
    console.print(f"Generated {len(phases)} phases. Starting at {start_qps} QPS, up to {max_qps} QPS.")
    if Confirm.ask("Start Stress Test?"):
        stresstest(count, phases, mock=False, console=console)

def main_menu():
    while True:
        console.print(Panel.fit("[bold white]Technitium DNS Performance Suite[/bold white]", border_style="magenta"))
        print("[1] Prefill Cache (Incremental Async)")
        print("[2] Live Stress Test (Phased Load + Auto-Abort)")
        print("[3] Analyze Impact (Simulation)")
        print("[4] Monitor Active Background Process")
        print("[5] View History (SQLite)")
        print("[6] Sync Usage Data (Predictive Engine)")
        print("[7] Clear Cache (Flush)")
        print("[q] Quit")
        
        choice = Prompt.ask("\nAction", choices=["1", "2", "3", "4", "5", "6", "7", "q"], default="1")
        if choice == "1":
            prefill(
                int(Prompt.ask("Count", default="100000")), 
                int(Prompt.ask("QPS", default="250")), 
                threads=250, 
                randomize=Confirm.ask("Randomize?", default=True),
                console=console
            )
        elif choice == "2":
            interactive_stresstest()
        elif choice == "3":
            conn = init_db(); cursor = conn.cursor()
            cursor.execute('INSERT INTO runs (run_type, is_mock, status) VALUES (?, 0, "completed")', ('analysis_only',))
            rid = cursor.lastrowid; conn.commit(); conn.close()
            run_analysis(run_id=rid, console=console)
        elif choice == "4": monitor_progress()
        elif choice == "5": view_history(console)
        elif choice == "6": sync_popularity(mock=False)
        elif choice == "7":
            if Confirm.ask("Flush cache?"): 
                res = api_call("cache/flush")
                if res.get("status") == "ok": print("✓ Cache Flushed.")
        elif choice == "q": break
        input("\nPress Enter...")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    
    p_prefill = subparsers.add_parser("prefill")
    p_prefill.add_argument("--count", type=int, default=100000)
    p_prefill.add_argument("--qps", type=int, default=250)
    p_prefill.add_argument("--random", action="store_true")
    
    p_stress = subparsers.add_parser("stresstest")
    p_stress.add_argument("--count", type=int, default=500000)
    
    subparsers.add_parser("analyze")
    subparsers.add_parser("history")
    subparsers.add_parser("monitor")
    subparsers.add_parser("sync-usage")
    subparsers.add_parser("clear")
    args = parser.parse_args()
    
    if args.command == "prefill":
        prefill(args.count, args.qps, threads=250, mock=args.mock, randomize=args.random, console=console)
    elif args.command == "stresstest":
        # Default phases for CLI usage
        phases = [(250, 60), (300, 90), (400, 120), (600, 120), (800, 120), (1000, 120)]
        stresstest(args.count, phases, mock=args.mock, console=console)
    elif args.command == "analyze":
        conn = init_db(); cursor = conn.cursor()
        cursor.execute('INSERT INTO runs (run_type, is_mock, status) VALUES (?, ?, "completed")', ('analysis_only', int(args.mock)))
        rid = cursor.lastrowid; conn.commit(); conn.close()
        run_analysis(mock=args.mock, run_id=rid, console=console)
    elif args.command == "history":
        view_history(console)
    elif args.command == "monitor":
        monitor_progress()
    elif args.command == "sync-usage":
        sync_popularity(mock=args.mock)
    elif args.command == "clear":
        print("Clearing cache...") if args.mock else api_call("cache/flush")
        print("✓ Cache Flushed.")
    else: 
        main_menu()
