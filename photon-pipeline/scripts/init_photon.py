import pexpect
import sys
import os

def init_photon(ip, old_pass, new_password, pubkey):
    print(f"Initializing Photon OS at {ip}...")
    
    cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@{ip}"
    child = pexpect.spawn(cmd, timeout=30)
    
    # Handle initial password prompt
    passwords = [old_pass, new_password]
    for p in passwords:
        i = child.expect(['[Pp]assword:', '#', pexpect.EOF, pexpect.TIMEOUT])
        if i == 0:
            child.sendline(p)
        elif i == 1:
            break # Already logged in
        else:
            print("Failed to get prompt")
            sys.exit(1)
            
    # Now check if we need a password change or if we are in
    j = child.expect(['[Cc]urrent', '#', '[Pp]assword:'])
    if j == 0:
        # Mandatory password change prompt
        child.sendline(old_pass)
        child.expect('[Nn]ew password')
        child.sendline(new_password)
        child.expect('[Rr]etype new password')
        child.sendline(new_password)
        child.expect('#')
    elif j == 2:
        # If it asks for password yet again, it might be the new one?
        child.sendline(new_password)
        child.expect('#')
        
    print("Logged in as root. Installing sudo and setting up ansible user...")
    
    setup_cmds = [
        "tdnf install -y sudo",
        "useradd -m -G sudo -s /bin/bash ansible || echo 'User exists'",
        f"echo 'ansible:{new_password}' | chpasswd",
        f"mkdir -p /home/ansible/.ssh",
        f"echo '{pubkey}' > /home/ansible/.ssh/authorized_keys",
        "chown -R ansible:ansible /home/ansible/.ssh",
        "chmod 700 /home/ansible/.ssh",
        "chmod 600 /home/ansible/.ssh/authorized_keys",
        "echo 'ansible ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ansible",
        "sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config",
        "systemctl restart sshd"
    ]
    
    for c in setup_cmds:
        child.sendline(c)
        child.expect('#')
        
    print("Initialization complete.")
    child.sendline('exit')
    child.close()

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: init_photon.py <ip> <old_pass> <new_password> <pubkey>")
        sys.exit(1)
    init_photon(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
