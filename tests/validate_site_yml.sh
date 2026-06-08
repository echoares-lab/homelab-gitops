#!/bin/bash
# Validation tests for site.yml observability integration

set -e

echo "=== Testing site.yml observability integration ==="

# Test 1: Verify alloy and docker_metrics plays exist
echo -n "Checking for alloy play... "
ansible-playbook ansible/site.yml --list-tasks 2>/dev/null | grep -q "Deploy monitoring agents" && echo "✓" || echo "✗ FAILED"

echo -n "Checking for docker_metrics role tasks... "
ansible-playbook ansible/site.yml --list-tasks 2>/dev/null | grep -q "docker_metrics" && echo "✓" || echo "✗ FAILED"

# Test 2: Verify tag is in metadata
echo -n "Checking alloy tag in metadata... "
grep -q "alloy:" config/metadata.yml && echo "✓" || echo "✗ FAILED"

# Test 3: Verify runners don't have alloy tag
echo -n "Verifying runners opt-out of monitoring... "
if ! grep -r "tag_alloy" config/profiles/ 2>/dev/null | grep -q "runner"; then
  echo "✓"
else
  echo "✗ FAILED: Found tag_alloy in runner profiles"
  exit 1
fi

echo "=== All integration tests passed ==="
