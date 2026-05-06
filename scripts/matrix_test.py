import subprocess
import os
import sys
import time
import pexpect

# Configuration
TEST_PROFILE = "matrix-test-node"
TEST_IP = "10.10.10.119"
TEST_GW = "10.10.10.1"

def log(msg):
    print(f"\n[MATRIX TEST] {msg}")

def run_cmd(cmd):
    print(f"Running: {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        print(f"Error: Command failed with code {res.returncode}")
        print(f"STDOUT: {res.stdout}")
        print(f"STDERR: {res.stderr}")
        sys.exit(res.returncode)
    return res.stdout

def test_generators():
    log("Testing Generators...")
    # 1. Create Profile
    if os.path.exists(f"config/profiles/{TEST_PROFILE}.yml"):
        os.remove(f"config/profiles/{TEST_PROFILE}.yml")
        
    child = pexpect.spawn(f"python3 manage.py create-profile")
    child.expect("Enter new profile name:")
    child.sendline(TEST_PROFILE)
    child.expect("Base OS")
    child.sendline("1") # Ubuntu
    child.expect("CPU Count")
    child.sendline("2")
    child.expect("RAM")
    child.sendline("4")
    child.expect("Disk Size")
    child.sendline("20")
    child.expect("Extra Tags")
    child.sendline("matrix_test")
    child.expect(pexpect.EOF)
    
    if not os.path.exists(f"config/profiles/{TEST_PROFILE}.yml"):
        print("Error: Profile generation failed.")
        sys.exit(1)
    log("Generator test PASSED.")

def test_logic_audit():
    log("Testing Orchestrator Logic...")
    
    # 1. Lint the new profile
    out = run_cmd(f"python3 manage.py lint {TEST_PROFILE} 01")
    if "Infrastructure Linting Passed" not in out:
        print("Error: Linting failed.")
        sys.exit(1)
        
    # 2. Check help menu
    out = run_cmd("python3 manage.py --help")
    if "Synthesis" not in out:
        print("Error: Help menu malformed.")
        sys.exit(1)
    
    log("Logic audit PASSED.")

def main():
    log("Starting Matrix Testing Suite...")
    
    try:
        test_generators()
        test_logic_audit()
        
        # Cleanup
        if os.path.exists(f"config/profiles/{TEST_PROFILE}.yml"):
            os.remove(f"config/profiles/{TEST_PROFILE}.yml")
            
        log("MATRIX TEST COMPLETED SUCCESSFULLY")
    except Exception as e:
        print(f"Matrix test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
