import time
import socket
from typing import Callable, Dict, Any

class DoctorService:
    """Service to run diagnostics on core systems."""

    def __init__(self, health_checks: Dict[str, Any], dns_resolver: Callable[[str], str] = socket.gethostbyname):
        self.health_checks = health_checks
        self.dns_resolver = dns_resolver

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run health checks on core systems."""
        results = {}

        for component, provider in self.health_checks.items():
            start = time.time()
            try:
                provider.validate()
                results[component] = {"status": "pass", "latency": time.time() - start}
            except Exception as e:
                results[component] = {"status": "fail", "error": str(e)}

        # Check DNS Resolution
        start = time.time()
        try:
            self.dns_resolver("1.1.1.1")
            results["dns"] = {"status": "pass", "latency": time.time() - start}
        except socket.error as e:
            results["dns"] = {"status": "fail", "error": str(e)}

        return results
