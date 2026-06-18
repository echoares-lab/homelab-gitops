import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ComparisonEngine:
    """Compare baseline and optimized performance results."""

    def compare_results(self, baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare baseline and optimized results.

        Args:
            baseline: Baseline result dictionary
            optimized: Optimized result dictionary

        Returns:
            Comparison dictionary with baseline, optimized, and delta
        """
        comparison = {
            'baseline': baseline,
            'optimized': optimized,
            'delta': {}
        }

        baseline_metrics = baseline.get('metrics', {})
        optimized_metrics = optimized.get('metrics', {})

        # Calculate deltas for all metrics
        for key in baseline_metrics.keys():
            if key in optimized_metrics:
                baseline_val = baseline_metrics[key]
                optimized_val = optimized_metrics[key]

                if baseline_val != 0:
                    percent_change = ((optimized_val - baseline_val) / baseline_val) * 100
                else:
                    percent_change = 100 if optimized_val > 0 else 0

                comparison['delta'][key] = {
                    'baseline': baseline_val,
                    'optimized': optimized_val,
                    'absolute_change': optimized_val - baseline_val,
                    'percent_change': round(percent_change, 2)
                }

        logger.info(f"Comparison complete: {len(comparison['delta'])} metrics analyzed")
        return comparison

    def detect_regressions(self, comparison: Dict[str, Any], regression_threshold: float = 10.0) -> Dict[str, Any]:
        """
        Detect performance regressions above threshold.

        Args:
            comparison: Comparison result dictionary
            regression_threshold: Threshold % for regression detection

        Returns:
            Dictionary with detected regressions
        """
        regressions = {}

        for metric, delta in comparison.get('delta', {}).items():
            percent_change = delta.get('percent_change', 0)

            # For latency metrics (higher is worse), invert the logic
            if 'lat' in metric or 'latency' in metric:
                if percent_change > regression_threshold:
                    regressions[metric] = delta
                    logger.warning(f"REGRESSION detected: {metric} increased by {percent_change}%")
            # For IOPS/throughput (higher is better)
            else:
                if percent_change < -regression_threshold:
                    regressions[metric] = delta
                    logger.warning(f"REGRESSION detected: {metric} decreased by {abs(percent_change)}%")

        return regressions

    def detect_improvements(self, comparison: Dict[str, Any], improvement_threshold: float = 5.0) -> Dict[str, Any]:
        """
        Detect performance improvements above threshold.

        Args:
            comparison: Comparison result dictionary
            improvement_threshold: Threshold % for improvement detection

        Returns:
            Dictionary with detected improvements
        """
        improvements = {}

        for metric, delta in comparison.get('delta', {}).items():
            percent_change = delta.get('percent_change', 0)

            # For latency metrics (lower is better)
            if 'lat' in metric or 'latency' in metric:
                if percent_change < -improvement_threshold:
                    improvements[metric] = delta
                    logger.info(f"IMPROVEMENT detected: {metric} decreased by {abs(percent_change)}%")
            # For IOPS/throughput (higher is better)
            else:
                if percent_change > improvement_threshold:
                    improvements[metric] = delta
                    logger.info(f"IMPROVEMENT detected: {metric} increased by {percent_change}%")

        return improvements

    def generate_summary(self, comparison: Dict[str, Any]) -> str:
        """
        Generate human-readable comparison summary.

        Args:
            comparison: Comparison result dictionary

        Returns:
            Formatted summary string
        """
        summary = "=== Performance Comparison Summary ===\n"

        improvements = self.detect_improvements(comparison)
        regressions = self.detect_regressions(comparison)

        summary += f"\nBaseline: {comparison['baseline']['timestamp']}\n"
        summary += f"Optimized: {comparison['optimized']['timestamp']}\n"

        if improvements:
            summary += f"\n✓ Improvements ({len(improvements)}):\n"
            for metric, delta in improvements.items():
                summary += f"  {metric}: {delta['percent_change']:+.2f}% " \
                          f"({delta['baseline']:.2f} → {delta['optimized']:.2f})\n"

        if regressions:
            summary += f"\n✗ Regressions ({len(regressions)}):\n"
            for metric, delta in regressions.items():
                summary += f"  {metric}: {delta['percent_change']:+.2f}% " \
                          f"({delta['baseline']:.2f} → {delta['optimized']:.2f})\n"

        if not improvements and not regressions:
            summary += "\n(No significant changes detected)\n"

        return summary
