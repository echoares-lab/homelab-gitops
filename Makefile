.PHONY: sync-ci-runners apply-ci-runners help-ci-runners

help-ci-runners:
	@echo "CI runner aggregation (homelab-gitops)"
	@echo ""
	@echo "  make sync-ci-runners          Scan registered repos → ansible/generated/ci_runner/"
	@echo "  make apply-ci-runners         Ansible via vSphere inventory (runner VMs)"
	@echo "  make apply-ci-runners-local   Ansible on this host (local-ci-runner.ini)"
	@echo ""
	@echo "Add a repo: config/ci-runner-repos.yaml + requirements/ci-runner.manifest.yaml in that repo"

sync-ci-runners:
	python3 scripts/sync_ci_runner_requirements.py

APPLY_INVENTORY ?= ansible/inventory/vmware_vms.yml
APPLY_LIMIT ?= tag_git_test:tag_cf_runner

apply-ci-runners: sync-ci-runners
	ansible-playbook ansible/sync-github-ci-runners.yml \
	  -i $(APPLY_INVENTORY) \
	  --limit '$(APPLY_LIMIT)'

apply-ci-runners-local: sync-ci-runners
	ansible-playbook ansible/sync-github-ci-runners.yml \
	  -i ansible/inventory/local-ci-runner.ini
