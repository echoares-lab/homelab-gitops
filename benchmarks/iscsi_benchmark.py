#!/usr/bin/env python3
"""
iSCSI Datastore Benchmark Orchestrator

Main CLI tool for running FIO benchmarks on test VMs and comparing results.

Usage:
    python3 scripts/iscsi_benchmark.py --profile database --vms 5 --label baseline
    python3 scripts/iscsi_benchmark.py --compare baseline optimized-v1
    python3 scripts/iscsi_benchmark.py --capture-config --label baseline
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from benchmarks.ssh_executor import SSHExecutor
from benchmarks.metrics_parser import MetricsParser
from benchmarks.config_capturer import ConfigCapturer
from benchmarks.comparison_engine import ComparisonEngine
from benchmarks.report_generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class iSCSIBenchmark:
    """Main benchmark orchestrator."""

    def __init__(self, workload_dir: str = "benchmarks/workloads",
                 results_dir: str = "benchmarks/results",
                 vm_username: str = "ubuntu",
                 vm_key_path: str = None):
        """
        Initialize benchmark orchestrator.

        Args:
            workload_dir: Directory containing FIO workload files
            results_dir: Directory to store results
            vm_username: SSH username for test VMs
            vm_key_path: Path to SSH private key
        """
        self.workload_dir = Path(workload_dir)
        self.results_dir = Path(results_dir)
        self.vm_username = vm_username
        self.vm_key_path = vm_key_path
        self.metrics_parser = MetricsParser()
        self.comparison_engine = ComparisonEngine()
        self.report_generator = ReportGenerator()

        # Create results directory
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_benchmark(self, vm_ips: List[str], profile: str, label: str, duration: int = 60) -> List[dict]:
        """
        Run FIO benchmark on test VMs.

        Args:
            vm_ips: List of VM IP addresses
            profile: Workload profile name (database, sequential, mixed)
            label: Label for this benchmark run (baseline, optimized-v1)
            duration: Benchmark duration in seconds

        Returns:
            List of result dictionaries
        """
        workload_file = self.workload_dir / f"{profile}.fio"

        if not workload_file.exists():
            logger.error(f"Workload file not found: {workload_file}")
            return []

        results = []

        for vm_ip in vm_ips:
            try:
                logger.info(f"Running {profile} benchmark on {vm_ip}")
                result = self._run_benchmark_on_vm(vm_ip, workload_file, profile, label)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to benchmark {vm_ip}: {e}")
                continue

        return results

    def _run_benchmark_on_vm(self, vm_ip: str, workload_file: Path, profile: str, label: str) -> dict:
        """
        Run benchmark on a single VM.

        Args:
            vm_ip: VM IP address
            workload_file: Path to FIO config file
            profile: Workload profile name
            label: Benchmark label

        Returns:
            Result dictionary
        """
        with SSHExecutor(vm_ip, username=self.vm_username, key_path=self.vm_key_path) as executor:
            executor.connect()

            # Transfer workload file to VM
            remote_workload = f"/tmp/{workload_file.name}"
            executor.transfer_file(str(workload_file), remote_workload)

            # Run FIO with JSON output
            fio_cmd = f"fio {remote_workload} --output-format=json"
            output = executor.execute_command(fio_cmd)

            # Parse results
            fio_json = json.loads(output)
            metrics = self.metrics_parser.parse_fio_json(fio_json)

            # Save results
            result = {
                'vm_ip': vm_ip,
                'profile': profile,
                'label': label,
                'metrics': metrics,
                'raw_output': fio_json
            }

            return result

    def save_results(self, results: List[dict], profile: str, label: str) -> str:
        """
        Save benchmark results to JSON file.

        Args:
            results: List of result dictionaries
            profile: Workload profile name
            label: Benchmark label

        Returns:
            Path to saved results file
        """
        import time
        timestamp = time.strftime("%Y-%m-%d-%H%M%S")
        filename = self.results_dir / f"{timestamp}-{label}-{profile}.json"

        data = {
            'timestamp': timestamp,
            'profile': profile,
            'label': label,
            'results': results
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved results to {filename}")
        return str(filename)

    def load_results(self, filename: str) -> dict:
        """
        Load benchmark results from JSON file.

        Args:
            filename: Path to results file

        Returns:
            Results dictionary
        """
        with open(filename, 'r') as f:
            return json.load(f)

    def compare_runs(self, baseline_label: str, optimized_label: str) -> dict:
        """
        Compare two benchmark runs.

        Args:
            baseline_label: Label of baseline run
            optimized_label: Label of optimized run

        Returns:
            Comparison dictionary
        """
        # Load latest results for each label
        baseline_files = sorted(self.results_dir.glob(f"*-{baseline_label}-*.json"))
        optimized_files = sorted(self.results_dir.glob(f"*-{optimized_label}-*.json"))

        if not baseline_files or not optimized_files:
            logger.error("Could not find baseline or optimized results")
            return {}

        baseline_data = self.load_results(str(baseline_files[-1]))
        optimized_data = self.load_results(str(optimized_files[-1]))

        # Aggregate metrics across all VMs
        baseline_metrics = self._aggregate_metrics(baseline_data['results'])
        optimized_metrics = self._aggregate_metrics(optimized_data['results'])

        comparison = {
            'baseline': {
                'timestamp': baseline_data['timestamp'],
                'metrics': baseline_metrics
            },
            'optimized': {
                'timestamp': optimized_data['timestamp'],
                'metrics': optimized_metrics
            }
        }

        # Calculate deltas
        comparison['delta'] = {}
        for key in baseline_metrics.keys():
            if key in optimized_metrics:
                baseline_val = baseline_metrics[key]
                optimized_val = optimized_metrics[key]
                percent_change = ((optimized_val - baseline_val) / baseline_val * 100) if baseline_val != 0 else 0

                comparison['delta'][key] = {
                    'baseline': baseline_val,
                    'optimized': optimized_val,
                    'absolute_change': optimized_val - baseline_val,
                    'percent_change': round(percent_change, 2)
                }

        return comparison

    def _aggregate_metrics(self, results: List[dict]) -> dict:
        """
        Aggregate metrics across multiple VMs.

        Args:
            results: List of result dictionaries

        Returns:
            Aggregated metrics dictionary
        """
        if not results:
            return {}

        # Simple averaging for now
        aggregated = {}
        num_vms = len(results)

        for metric_key in results[0]['metrics'].keys():
            values = [r['metrics'][metric_key] for r in results if metric_key in r['metrics']]
            if values:
                aggregated[metric_key] = sum(values) / len(values)

        return aggregated

    def capture_config(self, label: str, truenas_host: str = "10.10.10.20",
                      truenas_api_key: str = None) -> str:
        """
        Capture system configuration.

        Args:
            label: Configuration label
            truenas_host: TrueNAS host IP
            truenas_api_key: TrueNAS API key

        Returns:
            Path to saved config file
        """
        capturer = ConfigCapturer(truenas_host, truenas_api_key)
        return capturer.save_config_snapshot(label)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='iSCSI Datastore Performance Benchmark Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Capture baseline configuration
  python3 benchmarks/iscsi_benchmark.py --capture-config --label baseline

  # Run database workload on 5 VMs
  python3 benchmarks/iscsi_benchmark.py --profile database --vms 5 --label baseline

  # Compare baseline vs optimized
  python3 benchmarks/iscsi_benchmark.py --compare baseline optimized-v1
"""
    )

    parser.add_argument('--profile', choices=['database', 'sequential', 'mixed'],
                       help='Workload profile to run')
    parser.add_argument('--vms', type=int, default=5,
                       help='Number of test VMs (default: 5)')
    parser.add_argument('--label', type=str,
                       help='Label for this run (e.g., baseline, optimized-v1)')
    parser.add_argument('--vm-ips', type=str, nargs='+',
                       help='Specific VM IP addresses to benchmark')
    parser.add_argument('--compare', type=str, nargs=2, metavar=('BASELINE', 'OPTIMIZED'),
                       help='Compare two benchmark runs')
    parser.add_argument('--capture-config', action='store_true',
                       help='Capture system configuration snapshot')
    parser.add_argument('--truenas-host', default='10.10.10.20',
                       help='TrueNAS host IP (default: 10.10.10.20)')
    parser.add_argument('--output-dir', default='benchmarks',
                       help='Output directory (default: benchmarks)')

    args = parser.parse_args()

    if not any([args.profile, args.compare, args.capture_config]):
        parser.print_help()
        return 1

    benchmark = iSCSIBenchmark()

    # Capture configuration
    if args.capture_config:
        if not args.label:
            logger.error("--label required with --capture-config")
            return 1
        config_file = benchmark.capture_config(args.label, args.truenas_host)
        logger.info(f"Configuration saved to {config_file}")

    # Run benchmark
    if args.profile:
        if not args.label:
            logger.error("--label required with --profile")
            return 1

        # Generate VM IPs if not provided
        if args.vm_ips:
            vm_ips = args.vm_ips
        else:
            vm_ips = [f"10.10.10.{100 + i}" for i in range(args.vms)]

        logger.info(f"Running {args.profile} benchmark on {len(vm_ips)} VMs with label '{args.label}'")
        results = benchmark.run_benchmark(vm_ips, args.profile, args.label)

        if results:
            results_file = benchmark.save_results(results, args.profile, args.label)
            logger.info(f"Benchmark complete: {results_file}")
        else:
            logger.error("No successful benchmark results")
            return 1

    # Compare runs
    if args.compare:
        baseline_label, optimized_label = args.compare
        comparison = benchmark.compare_runs(baseline_label, optimized_label)

        if comparison:
            # Generate reports
            reports = benchmark.report_generator.generate_all_reports(comparison)
            logger.info(f"Generated reports:")
            for report_type, report_path in reports.items():
                logger.info(f"  {report_type}: {report_path}")

            # Print summary
            summary = benchmark.comparison_engine.generate_summary(comparison)
            print(summary)
        else:
            logger.error("Comparison failed")
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
