import yaml
import subprocess
import os
import sys

def run_govc(args):
    # Load environment variables for govc
    env = os.environ.copy()
    env["GOVC_URL"] = env.get("VCENTER_SERVER")
    env["GOVC_USERNAME"] = env.get("VCENTER_USERNAME")
    env["GOVC_PASSWORD"] = env.get("VCENTER_PASSWORD")
    env["GOVC_INSECURE"] = "true"
    cmd = ["/home/gemini-cli/template-pipeline/build/govc"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result

def lint():
    profile = os.environ.get('RUNTIME_PROFILE', 'photon-docker')
    config_path = f"config/profiles/{profile}.yml"
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found")
        sys.exit(1)
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    vcenter = config.get('vcenter', {})
    dc = vcenter.get('datacenter')
    cluster = vcenter.get('cluster')
    ds = vcenter.get('datastore')
    network = vcenter.get('network')
    # Prioritize runtime host override
    host = os.environ.get('VCENTER_HOST_OVERRIDE', vcenter.get('host'))
    
    print(f"--- Linting vCenter Infrastructure ---")
    
    # Check objects via 'ls'
    checks = [
        {"name": "Datacenter", "path": f"/{dc}"},
        {"name": "Cluster", "path": f"/{dc}/host/{cluster}"},
        {"name": "Datastore", "path": f"/{dc}/datastore/{ds}"},
        {"name": "Network", "path": f"/{dc}/network/{network}"},
        {"name": "Host", "path": f"/{dc}/host/{cluster}/{host}"}
    ]
    
    for check in checks:
        res = run_govc(["ls", check["path"]])
        if res.returncode != 0 or not res.stdout.strip():
            print(f"[FAIL] {check['name']} '{check['path']}' not found")
            sys.exit(1)
        print(f"[OK] {check['name']}: {check['path']}")
    
    print(f"--- Infrastructure Linting Passed ---")

if __name__ == "__main__":
    lint()
