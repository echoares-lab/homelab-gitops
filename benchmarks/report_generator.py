import json
import csv
import logging
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate HTML and CSV performance reports."""

    def __init__(self, output_dir: str = "benchmarks/reports"):
        """Initialize report generator."""
        self.output_dir = output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, comparison: Dict[str, Any], title: str = "Performance Comparison") -> str:
        """
        Generate HTML comparison report.

        Args:
            comparison: Comparison result dictionary
            title: Report title

        Returns:
            Path to generated HTML file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        filename = f"{self.output_dir}/comparison-{timestamp}.html"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #007bff; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f9f9f9; }}
        .positive {{ color: green; font-weight: bold; }}
        .negative {{ color: red; font-weight: bold; }}
        .metric-name {{ font-weight: bold; width: 30%; }}
        .metric-value {{ width: 20%; text-align: right; }}
        .metric-change {{ width: 20%; text-align: right; }}
        .comparison-section {{ margin: 30px 0; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="summary">
            <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Baseline:</strong> {comparison['baseline']['timestamp']}</p>
            <p><strong>Optimized:</strong> {comparison['optimized']['timestamp']}</p>
        </div>

        <div class="comparison-section">
            <h2>Performance Metrics Comparison</h2>
            <table>
                <tr>
                    <th class="metric-name">Metric</th>
                    <th class="metric-value">Baseline</th>
                    <th class="metric-value">Optimized</th>
                    <th class="metric-change">Change</th>
                </tr>
"""

        for metric, delta in comparison.get('delta', {}).items():
            baseline_val = delta['baseline']
            optimized_val = delta['optimized']
            percent_change = delta['percent_change']

            # Determine if improvement or regression
            if 'lat' in metric:
                status_class = 'positive' if percent_change < 0 else 'negative'
            else:
                status_class = 'positive' if percent_change > 0 else 'negative'

            html_content += f"""                <tr>
                    <td class="metric-name">{metric}</td>
                    <td class="metric-value">{baseline_val:.2f}</td>
                    <td class="metric-value">{optimized_val:.2f}</td>
                    <td class="metric-change {status_class}">{percent_change:+.2f}%</td>
                </tr>
"""

        html_content += """            </table>
        </div>
    </div>
</body>
</html>
"""

        with open(filename, 'w') as f:
            f.write(html_content)

        logger.info(f"Generated HTML report: {filename}")
        return filename

    def generate_csv_report(self, comparison: Dict[str, Any], title: str = "Performance Metrics") -> str:
        """
        Generate CSV metrics report.

        Args:
            comparison: Comparison result dictionary
            title: Report title

        Returns:
            Path to generated CSV file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        filename = f"{self.output_dir}/metrics-{timestamp}.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write headers
            writer.writerow(['Metric', 'Baseline', 'Optimized', 'Absolute Change', 'Percent Change'])

            # Write data rows
            for metric, delta in comparison.get('delta', {}).items():
                writer.writerow([
                    metric,
                    f"{delta['baseline']:.2f}",
                    f"{delta['optimized']:.2f}",
                    f"{delta['absolute_change']:.2f}",
                    f"{delta['percent_change']:+.2f}%"
                ])

        logger.info(f"Generated CSV report: {filename}")
        return filename

    def generate_all_reports(self, comparison: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all report types.

        Args:
            comparison: Comparison result dictionary

        Returns:
            Dictionary with paths to generated reports
        """
        return {
            'html': self.generate_html_report(comparison),
            'csv': self.generate_csv_report(comparison)
        }
