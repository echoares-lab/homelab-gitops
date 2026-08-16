import requests
import json
import base64
import os
import sys

def get_screenshot(vm_name):
    # Vault configuration
    vault_addr = "http://openbao.plexplease.com:8201"
    
    # Get vCenter credentials from Vault
    auth_resp = requests.post(f"{vault_addr}/v1/auth/token/create", json={"policies": ["default"]})
    token = auth_resp.json()["auth"]["client_token"]
    
    headers = {"X-Vault-Token": token}
    creds_resp = requests.get(f"{vault_addr}/v1/kv/data/agents/autonomous/vcenter/prod", headers=headers)
    creds = creds_resp.json()["data"]["data"]
    vc_user = creds["VCENTER_USERNAME"]
    vc_pass = creds["VCENTER_PASSWORD"]

    # vCenter configuration
    vc_host = "vcenter.plexplease.com"
    
    # Session
    s = requests.Session()
    s.verify = False
    import urllib3
    urllib3.disable_warnings()
    
    # Login
    login_resp = s.post(f"https://{vc_host}/api/session", auth=(vc_user, vc_pass))
    login_resp.raise_for_status()
    s.headers.update({"vmware-api-session-id": login_resp.json()})
    
    # Get VM list to find ID
    vms_resp = s.get(f"https://{vc_host}/api/vcenter/vm")
    vm_id = None
    for vm in vms_resp.json():
        if vm["name"] == vm_name:
            vm_id = vm["vm"]
            break
            
    if not vm_id:
        print(f"VM {vm_name} not found")
        sys.exit(1)
        
    print(f"Found VM {vm_name} with ID {vm_id}")
    
    # Unfortunately the REST API doesn't have a direct screenshot endpoint that returns the image.
    # We must use govc for screenshots since it uses the SOAP API.
    # However we can just run govc via subprocess using the credentials we just pulled.

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: screenshot.py <vm-name>")
        sys.exit(1)
    get_screenshot(sys.argv[1])
