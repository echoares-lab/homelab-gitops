import time
import socket
from typing import Dict, Any
from homelab_gitops.drivers.vcenter_driver import vCenterDriver
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.tofu_driver import TofuDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError

class DoctorService:
    """Service to run diagnostics on core systems."""

    def __init__(self):
        self.vcenter = vCenterDriver()
        self.technitium = TechnitiumDriver()
        self.opnsense = OPNsenseDriver()
        self.tofu = TofuDriver()

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run health checks on core systems."""
        results = {}

        # Check vCenter
        start = time.time()
        try:
            self.vcenter.validate()
            results["vcenter"] = {"status": "pass", "latency": time.time() - start}
        except PrerequisiteError as e:
            results["vcenter"] = {"status": "fail", "error": str(e)}
        except Exception as e:
            results["vcenter"] = {"status": "fail", "error": str(e)}

        # Check Technitium
        start = time.time()
        try:
            self.technitium.validate()
            results["technitium"] = {"status": "pass", "latency": time.time() - start}
        except PrerequisiteError as e:
            results["technitium"] = {"status": "fail", "error": str(e)}
        except Exception as e:
            results["technitium"] = {"status": "fail", "error": str(e)}

        # Check OPNsense
        start = time.time()
        try:
            self.opnsense.validate()
            results["opnsense"] = {"status": "pass", "latency": time.time() - start}
        except PrerequisiteError as e:
            results["opnsense"] = {"status": "fail", "error": str(e)}
        except Exception as e:
            results["opnsense"] = {"status": "fail", "error": str(e)}

        # Check Tofu
        start = time.time()
        try:
            self.tofu.validate()
            results["tofu"] = {"status": "pass", "latency": time.time() - start}
        except PrerequisiteError as e:
            results["tofu"] = {"status": "fail", "error": str(e)}
        except Exception as e:
            results["tofu"] = {"status": "fail", "error": str(e)}

        # Check DNS Resolution
        start = time.time()
        try:
            socket.gethostbyname("1.1.1.1")
            results["dns"] = {"status": "pass", "latency": time.time() - start}
        except socket.error as e:
            results["dns"] = {"status": "fail", "error": str(e)}

        return results
