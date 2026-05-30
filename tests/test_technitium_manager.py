import os
import csv
import json
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from scripts.technitium_manager import app, _op_upsert, OP_VAULT
from typer.testing import CliRunner

runner = CliRunner()

def test_add_zone_interactively(tmp_path):
    csv_file = tmp_path / "test_records.csv"
    
    # Inputs: 1. resource_type=zone, 2. name=test.local, 3. type=Primary, 4. optional=y, 5. comments=My Zone, 6. depends_on=none
    inputs = ["zone", "test.local", "Primary", "y", "My Zone", ""]
    
    with patch("rich.prompt.Prompt.ask", side_effect=inputs):
        result = runner.invoke(app, ["add-resource"], env={"CSV_FILE": str(csv_file)})
    
def test_conversion_logic(tmp_path):
    csv_input = tmp_path / "input.csv"
    output_json = tmp_path / "output.tf.json"
    
    headers = [
        "resource_type", "name", "parent", "type", "value", "ttl", 
        "mac_address", "network_address", "subnet_mask", 
        "start_address", "end_address", "gateway", 
        "comments", "depends_on", "advanced_json"
    ]
    
    with open(csv_input, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        # Record
        writer.writerow(["record", "test.plex.com", "plex.com", "A", "10.0.0.1", "300", "", "", "", "", "", "", "Test", "", ""])
        # DHCP Scope
        writer.writerow(["dhcp_scope", "LAN", "", "", "", "", "", "192.168.1.0", "255.255.255.0", "192.168.1.10", "192.168.1.50", "192.168.1.1", "Home", "", ""])
    
    result = runner.invoke(app, ["convert-csv", "--csv", str(csv_input), "--output", str(output_json)])
    
    assert result.exit_code == 0
    with open(output_json, 'r') as f:
        data = json.load(f)
        resources = data["resource"]
        assert "technitium_dns_zone_record" in resources
        assert "technitium_dhcp_scope" in resources
        
        # Check record attributes
        rec = list(resources["technitium_dns_zone_record"].values())[0]
        assert rec["domain"] == "test.plex.com"
        assert rec["ip_address"] == "10.0.0.1"
        
        # Check scope attributes
        scope = list(resources["technitium_dhcp_scope"].values())[0]
        assert scope["network_address"] == "192.168.1.0"
        assert scope["gateway"] == "192.168.1.1"

def test_op_upsert_item_exists():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0)
        ]

        _op_upsert("TestItem", "username", "text", "admin")

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["op", "item", "get", "TestItem", "--vault", OP_VAULT],
            capture_output=True, timeout=10
        )
        mock_run.assert_any_call(
            ["op", "item", "edit", "TestItem", "--vault", OP_VAULT, "username[text]=admin", "--format", "json"],
            capture_output=True, check=True, timeout=10
        )

def test_op_upsert_item_not_exists():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=0)
        ]

        _op_upsert("TestItem", "username", "text", "admin")

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["op", "item", "get", "TestItem", "--vault", OP_VAULT],
            capture_output=True, timeout=10
        )
        mock_run.assert_any_call(
            ["op", "item", "create", "--category", "Login", "--title", "TestItem", "--vault", OP_VAULT, "username[text]=admin", "--format", "json"],
            capture_output=True, check=True, timeout=10
        )

def test_op_upsert_edit_fails():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(returncode=0),
            subprocess.CalledProcessError(1, ["op", "item", "edit"])
        ]

        with pytest.raises(subprocess.CalledProcessError):
            _op_upsert("TestItem", "username", "text", "admin")
