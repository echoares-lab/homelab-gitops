import os
import csv
import pytest
from unittest.mock import patch
from scripts.dns_helper import app
from typer.testing import CliRunner

runner = CliRunner()

def test_add_record_creates_csv(tmp_path):
    csv_file = tmp_path / "test_records.csv"
    
    # Mock inputs for the interactive Prompt.ask calls
    # 1. Zone, 2. Domain, 3. Type, 4. Data, 5. TTL, 6. Comments
    inputs = ["example.com", "www.example.com", "A", "1.2.3.4", "300", "Test record"]
    
    with patch("rich.prompt.Prompt.ask", side_effect=inputs):
        result = runner.invoke(app, ["add-record", "--csv", str(csv_file)])
    
    assert result.exit_code == 0
    assert os.path.exists(csv_file)
    
    with open(csv_file, mode='r') as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["zone"] == "example.com"
        assert reader[0]["domain"] == "www.example.com"
        assert reader[0]["type"] == "A"
        assert reader[0]["data"] == "1.2.3.4"
        assert reader[0]["ttl"] == "300"
        assert reader[0]["comments"] == "Test record"

def test_convert_csv_to_json(tmp_path):
    csv_file = tmp_path / "records.csv"
    output_json = tmp_path / "records.tf.json"
    
    # Create a dummy CSV
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["zone", "domain", "type", "data", "ttl", "comments"])
        writer.writerow(["plex.com", "dns.plex.com", "A", "10.0.0.1", "3600", "Prod"])
    
    result = runner.invoke(app, ["convert-csv", str(csv_file), "--output", str(output_json)])
    
    assert result.exit_code == 0
    assert os.path.exists(output_json)
    
    import json
    with open(output_json, 'r') as f:
        data = json.load(f)
        assert "resource" in data
        assert "technitium_dns_zone" in data["resource"]
        assert "technitium_dns_zone_record" in data["resource"]
        # Check if record exists
        records = data["resource"]["technitium_dns_zone_record"]
        found = any(v["domain"] == "dns.plex.com" for v in records.values())
        assert found
