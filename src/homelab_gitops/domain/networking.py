"""Networking domain service for OPNsense orchestration."""

import logging
from typing import Dict, Any, Optional, List
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.domain.exceptions import DomainError

logger = logging.getLogger(__name__)


class NetworkingService:
    """Orchestrate OPNsense firewall and network lifecycle operations."""

    def __init__(self, driver: Optional[OPNsenseDriver] = None):
        """Initialize service with an OPNsense driver."""
        self.driver = driver or OPNsenseDriver()

    def prepare_node_network(self, profile: NodeProfile) -> List[TaskResult]:
        """Prepare VLAN and Firewall rules for a node profile.

        Args:
            profile: The node profile containing networking configuration.

        Returns:
            List of TaskResult objects for each operation performed.
        """
        results = []
        networking_config = profile.networking
        if not networking_config:
            logger.info(f"No networking configuration for profile: {profile.name}")
            return results

        # 1. Handle VLAN
        vlan_config = networking_config.get('vlan')
        if vlan_config and vlan_config.get('enabled', True):
            vlan_id = vlan_config.get('id')
            vlan_interface = vlan_config.get('interface')
            vlan_name = vlan_config.get('name', f"VLAN for {profile.name}")

            if vlan_id and vlan_interface:
                # Check if VLAN already exists (idempotency)
                existing_vlans_res = self.driver.execute(Task(
                    type="vlan",
                    profile=profile,
                    overrides={"resource": "vlan", "action": "list"}
                ))
                
                existing_vlans = existing_vlans_res.output.get('vlans', [])
                # OPNsense vlan list rows typically have 'tag' (vlan_id) and 'descr'
                vlan_exists = any(
                    str(v['tag']) == str(vlan_id) and v['if'] == vlan_interface
                    for v in existing_vlans
                )

                if not vlan_exists:
                    logger.info(f"Creating VLAN {vlan_id} on {vlan_interface}")
                    vlan_task = Task(
                        type="vlan",
                        profile=profile,
                        overrides={
                            "resource": "vlan",
                            "action": "create",
                            "interface": vlan_interface,
                            "vlan_id": vlan_id,
                            "description": vlan_name,
                        }
                    )
                    results.append(self.driver.execute(vlan_task))
                else:
                    logger.info(f"VLAN {vlan_id} already exists on {vlan_interface}")
                    results.append(TaskResult(
                        success=True,
                        task_type="vlan",
                        output={"status": "skipped", "reason": "already_exists"},
                        duration=0.0
                    ))

        # 2. Handle Firewall Rules
        rules = networking_config.get('firewall_rules', [])
        if rules:
            # Get existing rules for idempotency check
            existing_rules_res = self.driver.execute(Task(
                type="firewall",
                profile=profile,
                overrides={"resource": "firewall", "action": "list"}
            ))
            existing_rules = existing_rules_res.output.get('rules', [])

            for rule in rules:
                if not rule.get('enabled', True):
                    continue

                rule_name = rule.get('name')
                # Check if rule already exists by name
                rule_exists = any(r['description'] == rule_name for r in existing_rules)

                if not rule_exists:
                    logger.info(f"Creating firewall rule: {rule_name}")
                    rule_task = Task(
                        type="firewall",
                        profile=profile,
                        overrides={
                            "resource": "firewall",
                            "action": "create",
                            "name": rule_name,
                            "src_net": rule.get('src_net'),
                            "dst_net": rule.get('dst_net'),
                            "protocol": rule.get('protocol'),
                            "port": rule.get('port'),
                            "rule_action": rule.get('action', 'pass'),
                            "description": rule.get('description', rule_name),
                        }
                    )
                    results.append(self.driver.execute(rule_task))
                else:
                    logger.info(f"Firewall rule already exists: {rule_name}")
                    results.append(TaskResult(
                        success=True,
                        task_type="firewall",
                        output={"status": "skipped", "reason": "already_exists", "name": rule_name},
                        duration=0.0
                    ))

        return results

    def cleanup_node_network(self, profile: NodeProfile) -> List[TaskResult]:
        """Cleanup networking resources for a node profile.

        Args:
            profile: The node profile containing networking configuration.

        Returns:
            List of TaskResult objects for each operation performed.
        """
        results = []
        networking_config = profile.networking
        if not networking_config:
            return results

        # 1. Cleanup Firewall Rules
        rules = networking_config.get('firewall_rules', [])
        if rules:
            existing_rules_res = self.driver.execute(Task(
                type="firewall",
                profile=profile,
                overrides={"resource": "firewall", "action": "list"}
            ))
            existing_rules = existing_rules_res.output.get('rules', [])

            for rule in rules:
                rule_name = rule.get('name')
                # Find rule UUID by name
                # OPNsense rules list has 'uuid' and 'description' (which we use as name)
                matching_rules = [r for r in existing_rules if r['description'] == rule_name]
                for r in matching_rules:
                    uuid = r.get('uuid')
                    if uuid:
                        logger.info(f"Deleting firewall rule: {rule_name} ({uuid})")
                        del_task = Task(
                            type="firewall",
                            profile=profile,
                            overrides={
                                "resource": "firewall",
                                "action": "delete",
                                "uuid": uuid
                            }
                        )
                        results.append(self.driver.execute(del_task))

        # 2. Cleanup VLAN
        vlan_config = networking_config.get('vlan')
        if vlan_config:
            vlan_id = vlan_config.get('id')
            vlan_interface = vlan_config.get('interface')
            
            if vlan_id and vlan_interface:
                existing_vlans_res = self.driver.execute(Task(
                    type="vlan",
                    profile=profile,
                    overrides={"resource": "vlan", "action": "list"}
                ))
                existing_vlans = existing_vlans_res.output.get('vlans', [])
                
                # Find VLAN UUID by tag and interface
                matching_vlans = [
                    v for v in existing_vlans 
                    if str(v['tag']) == str(vlan_id) and v['if'] == vlan_interface
                ]
                for v in matching_vlans:
                    uuid = v.get('uuid')
                    if uuid:
                        logger.info(f"Deleting VLAN {vlan_id} ({uuid})")
                        del_task = Task(
                            type="vlan",
                            profile=profile,
                            overrides={
                                "resource": "vlan",
                                "action": "delete",
                                "uuid": uuid
                            }
                        )
                        results.append(self.driver.execute(del_task))

        return results
