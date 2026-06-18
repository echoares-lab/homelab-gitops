import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MetricsParser:
    """Parse FIO JSON output and extract performance metrics."""

    def parse_fio_json(self, fio_output: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract metrics from FIO JSON output.

        Args:
            fio_output: Parsed FIO JSON output

        Returns:
            Dictionary of extracted metrics
        """
        metrics = {}

        try:
            for job in fio_output.get('jobs', []):
                # Extract IOPS
                read_iops = job.get('read', {}).get('iops', 0)
                write_iops = job.get('write', {}).get('iops', 0)

                metrics['read_iops'] = read_iops
                metrics['write_iops'] = write_iops
                metrics['total_iops'] = read_iops + write_iops

                # Extract latency percentiles (convert ns to ms)
                read_lat = job.get('read', {}).get('clat_ns', {}).get('percentile', {})
                write_lat = job.get('write', {}).get('clat_ns', {}).get('percentile', {})

                for percentile in ['50.000000', '95.000000', '99.000000', '100.000000']:
                    p_value = int(percentile.split('.')[0])
                    if percentile in read_lat:
                        metrics[f'read_lat_p{p_value}_ms'] = read_lat[percentile] / 1_000_000
                    if percentile in write_lat:
                        metrics[f'write_lat_p{p_value}_ms'] = write_lat[percentile] / 1_000_000

                # Extract throughput (bw_mean in KB/s, convert to MB/s)
                read_bw = job.get('read', {}).get('bw_mean', 0)
                write_bw = job.get('write', {}).get('bw_mean', 0)

                metrics['read_throughput_mb'] = read_bw / 1000
                metrics['write_throughput_mb'] = write_bw / 1000
                metrics['total_throughput_mb'] = (read_bw + write_bw) / 1000

        except (KeyError, TypeError) as e:
            logger.error(f"Failed to parse FIO output: {e}")
            raise

        logger.info(f"Extracted metrics: IOPS={metrics.get('total_iops', 0)}, "
                   f"p99_lat={metrics.get('read_lat_p99_ms', 0):.2f}ms")
        return metrics

    def compare_metrics(self, baseline: Dict[str, float], current: Dict[str, float]) -> Dict[str, Any]:
        """
        Compare baseline and current metrics, calculate deltas.

        Args:
            baseline: Baseline metrics dictionary
            current: Current metrics dictionary

        Returns:
            Dictionary with baseline, current, and delta values
        """
        comparison = {
            'baseline': baseline,
            'current': current,
            'delta': {}
        }

        for key in baseline.keys():
            if key in current:
                baseline_val = baseline[key]
                current_val = current[key]

                if baseline_val != 0:
                    percent_change = ((current_val - baseline_val) / baseline_val) * 100
                else:
                    percent_change = 0 if current_val == 0 else 100

                comparison['delta'][key] = {
                    'absolute': current_val - baseline_val,
                    'percent': percent_change
                }

        return comparison
