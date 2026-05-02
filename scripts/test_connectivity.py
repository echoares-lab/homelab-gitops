import socket
import sys
import time

def check_ssh(ip, timeout=300):
    print(f"Waiting for SSH (Port 22) on {ip}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((ip, 22), timeout=5):
                print(f"[OK] SSH is reachable on {ip}")
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            print(f"Still waiting for {ip}:22...")
            time.sleep(10)
            
    print(f"[FAIL] Timeout reached waiting for SSH on {ip}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_connectivity.py <ip_address>")
        sys.exit(1)
    
    ip = sys.argv[1]
    if not check_ssh(ip):
        sys.exit(1)
