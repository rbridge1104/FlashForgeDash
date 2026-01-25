"""
Test script to verify printer visibility and connection.

Usage:
    python test_socket.py <printer_ip>

Example:
    python test_socket.py 192.168.1.100
"""

import socket
import sys
import time


def test_tcp_connection(ip: str, port: int = 8899, timeout: float = 5.0) -> bool:
    """Test basic TCP connectivity to the printer."""
    print(f"Testing TCP connection to {ip}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        print(f"  [OK] TCP connection successful")
        sock.close()
        return True
    except socket.timeout:
        print(f"  [FAIL] Connection timed out")
        return False
    except ConnectionRefusedError:
        print(f"  [FAIL] Connection refused - printer may be off or busy")
        return False
    except socket.error as e:
        print(f"  [FAIL] Socket error: {e}")
        return False


def test_handshake(ip: str, port: int = 8899, timeout: float = 5.0) -> bool:
    """Test M601 S1 handshake with the printer."""
    print(f"Testing M601 S1 handshake...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # Send handshake
        sock.sendall(b"~M601 S1\r\n")

        # Read response
        response = b""
        while True:
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b"ok" in response.lower() or b"error" in response.lower():
                    break
            except socket.timeout:
                break

        sock.close()

        response_str = response.decode('utf-8', errors='ignore')
        print(f"  Response: {response_str.strip()}")

        if "ok" in response_str.lower():
            print(f"  [OK] Handshake successful")
            return True
        else:
            print(f"  [FAIL] Handshake failed")
            return False

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_temperature_query(ip: str, port: int = 8899, timeout: float = 5.0) -> bool:
    """Test M105 temperature query."""
    print(f"Testing M105 temperature query...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # Handshake first
        sock.sendall(b"~M601 S1\r\n")
        time.sleep(0.5)
        sock.recv(1024)  # Clear handshake response

        # Send temperature query
        sock.sendall(b"~M105\r\n")

        # Read response
        response = b""
        while True:
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b"ok" in response.lower():
                    break
            except socket.timeout:
                break

        sock.close()

        response_str = response.decode('utf-8', errors='ignore')
        print(f"  Response: {response_str.strip()}")

        if "T0:" in response_str or "T:" in response_str:
            print(f"  [OK] Temperature query successful")
            return True
        else:
            print(f"  [WARN] Unexpected response format")
            return False

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_status_query(ip: str, port: int = 8899, timeout: float = 5.0) -> bool:
    """Test M119 status query."""
    print(f"Testing M119 status query...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # Handshake first
        sock.sendall(b"~M601 S1\r\n")
        time.sleep(0.5)
        sock.recv(1024)  # Clear handshake response

        # Send status query
        sock.sendall(b"~M119\r\n")

        # Read response
        response = b""
        while True:
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b"ok" in response.lower():
                    break
            except socket.timeout:
                break

        sock.close()

        response_str = response.decode('utf-8', errors='ignore')
        print(f"  Response: {response_str.strip()}")
        print(f"  [OK] Status query completed")
        return True

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_camera_stream(ip: str, port: int = 8080, timeout: float = 5.0) -> bool:
    """Test if camera stream is accessible."""
    print(f"Testing camera stream at http://{ip}:{port}/?action=stream...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # Send HTTP GET request
        request = f"GET /?action=stream HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n"
        sock.sendall(request.encode())

        # Read response header
        response = sock.recv(1024)
        sock.close()

        response_str = response.decode('utf-8', errors='ignore')

        if "200" in response_str or "multipart" in response_str.lower():
            print(f"  [OK] Camera stream accessible")
            return True
        else:
            print(f"  [WARN] Unexpected response: {response_str[:100]}")
            return False

    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_socket.py <printer_ip>")
        print("Example: python test_socket.py 192.168.1.100")
        sys.exit(1)

    ip = sys.argv[1]
    print(f"\n{'='*50}")
    print(f"FlashForge Adventurer 3 Connection Test")
    print(f"Target: {ip}")
    print(f"{'='*50}\n")

    results = {
        "TCP Connection": test_tcp_connection(ip),
        "Handshake (M601)": test_handshake(ip),
        "Temperature (M105)": test_temperature_query(ip),
        "Status (M119)": test_status_query(ip),
        "Camera Stream": test_camera_stream(ip),
    }

    print(f"\n{'='*50}")
    print("Summary:")
    print(f"{'='*50}")
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")

    all_passed = all(results.values())
    print(f"\n{'All tests passed!' if all_passed else 'Some tests failed.'}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
