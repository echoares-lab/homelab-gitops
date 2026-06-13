"""DHCP Migration domain service."""

import logging
from typing import Dict, Any
from homelab_gitops.domain.exceptions import DomainError
from homelab_gitops.domain.models import Task

logger = logging.getLogger(__name__)


class MigrationService:
    """Orchestrate DHCP migration from OPNsense to Technitium."""

    def __init__(self, opnsense_driver=None,
                 technitium_driver=None,
                 migration_driver=None):
        """Initialize service with required drivers."""
        from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
        from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
        from homelab_gitops.drivers.migration_driver import MigrationDriver

        self.opnsense = opnsense_driver or OPNsenseDriver()
        self.technitium = technitium_driver or TechnitiumDriver()
        self.migration = migration_driver or MigrationDriver(
            opnsense_driver=self.opnsense,
            technitium_driver=self.technitium
        )

    def discover(self) -> Dict[str, Any]:
        """Step 1: Discovery of DHCP interfaces and scopes.

        Returns:
            Dict containing enabled OPNsense interfaces and Technitium scopes.
        """
        try:
            opn_res = self.opnsense.execute(Task(
                type="dhcp",
                profile=None,  # Not needed for discovery
                overrides={"resource": "dhcp", "action": "list_enabled"}
            ))

            tech_res = self.technitium.execute(Task(
                type="dhcp",
                profile=None,
                overrides={"resource": "dhcp", "action": "list"}
            ))

            return {
                "opnsense_interfaces": opn_res.output.get("interfaces", []),
                "technitium_scopes": tech_res.output.get("scopes", [])
            }
        except Exception as e:
            raise DomainError(f"Discovery failed: {str(e)}")

    def migrate_dhcp(self, source: str, target: str) -> Dict[str, Any]:
        """Migrate a single DHCP interface from OPNsense to Technitium.

        Args:
            source: OPNsense interface name (e.g., 'opt1').
            target: Technitium scope name (e.g., 'MGMT').

        Returns:
            Dict with migration result.
        """
        # Step 2 & 3: Mapping & Pre-flight
        discovery = self.discover()

        # Validate source
        if not any(iface['interface'] == source for iface in discovery['opnsense_interfaces']):
            raise DomainError(f"Source interface '{source}' not enabled for DHCP in OPNsense")

        # Validate target
        if not any(scope['name'] == target for scope in discovery['technitium_scopes']):
            raise DomainError(f"Target scope '{target}' not found in Technitium")

        # Step 4: Cutover
        migrated = self.migration.load_state()

        # Check if already migrated
        if any(m['opnsense_interface'] == source for m in migrated):
            return {"status": "already_migrated", "interface": source, "scope": target}

        try:
            logger.info(f"Starting cutover: {source} -> {target}")

            # Disable OPNsense
            self.opnsense.execute(Task(
                type="dhcp",
                profile=None,
                overrides={"resource": "dhcp", "action": "disable", "interface": source}
            ))

            # Enable Technitium
            self.technitium.execute(Task(
                type="dhcp",
                profile=None,
                overrides={"resource": "dhcp", "action": "enable", "name": target}
            ))

            # Update state
            migrated.append({
                "opnsense_interface": source,
                "technitium_scope": target
            })
            self.migration.save_state(migrated)

            return {"status": "success", "interface": source, "scope": target}

        except Exception as e:
            logger.error(f"Migration failed for {source}: {e}. Initiating rollback...")
            rollback_res = self.rollback()
            raise DomainError(f"Migration failed: {e}. Rollback status: {rollback_res.get('status')}")

    def rollback(self) -> Dict[str, Any]:
        """Roll back all migrated scopes found in state."""
        res = self.migration.execute(Task(
            type="migration",
            profile=None,
            overrides={"action": "rollback"}
        ))
        return res.output
