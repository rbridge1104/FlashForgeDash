import socket
import requests
import yaml
from pathlib import Path

def load_config():
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def check_port(ip, port):
    print(f"Checking connection to {ip}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((ip, port))
    sock.close()
    if result == 0:
        print(f"  [SUCCESS] Port {port} is OPEN.")
        return True
    else:
        print(f"  [FAILURE] Port {port} is CLOSED or unreachable. (Error code: {result})")
        return False

def check_stream_url(ip, port):
    url = f"http://{ip}:{port}/?action=stream"
    print(f"Checking stream URL: {url}...")
    try:
        response = requests.get(url, stream=True, timeout=5)
        if response.status_code == 200:
            print(f"  [SUCCESS] HTTP 200 OK. Content-Type: {response.headers.get('content-type')}")
            return True
        else:
            print(f"  [FAILURE] HTTP {response.status_code}.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [FAILURE] Request failed: {e}")
        return False

def main():
    config = load_config()
    printer_config = config.get("printer", {})
    ip = printer_config.get("ip_address")
    
    if not ip:
        print("Error: 'printer.ip_address' not found in config.yaml")
        return

    port = printer_config.get("camera_port", 8080)
    
    print(f"--- FlashForge Camera Diagnostics ---")
    print(f"Target: {ip}")
    
    if check_port(ip, port):
        check_stream_url(ip, port)
    
    print("\nTips:")
    print("1. Ensure the camera is enabled in the printer settings (Tools > Settings > Camera).")
    print("2. Ensure no USB drive is plugged into the printer (camera/USB share the same bus).")

if __name__ == "__main__":
    main()
