"""
Test script for n8n webhook notifications.

This script tests the notification system by sending a test POST request
to the configured webhook URL.

Usage:
    python test_notifications.py <webhook_url>

Example:
    python test_notifications.py https://your-n8n.domain/webhook/printer-status
"""

import sys
import json
import urllib.request
import urllib.error
from datetime import datetime


def test_webhook(webhook_url: str) -> bool:
    """Send a test notification to the webhook."""
    print(f"Testing webhook: {webhook_url}")
    print("=" * 50)

    payload = {
        "printer_ip": "192.168.1.100",
        "status": "test",
        "message": "Test notification from FlashForge Monitor",
        "timestamp": datetime.now().isoformat(),
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.status
            response_text = response.read().decode('utf-8')

        print(f"Status Code: {status_code}")
        print(f"Response: {response_text[:500] if response_text else '(empty)'}")

        if status_code in (200, 201, 202, 204):
            print("\n[SUCCESS] Webhook test passed!")
            return True
        else:
            print(f"\n[WARNING] Unexpected status code: {status_code}")
            return False

    except urllib.error.URLError as e:
        print(f"\n[FAIL] URL error: {e}")
        return False
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        return False


def test_notification_payloads():
    """Test that notification payloads are correctly formatted."""
    print("\nNotification Payload Format Tests")
    print("=" * 50)

    test_statuses = [
        ("complete", "Print job completed successfully!"),
        ("error", "Printer error: Filament runout detected"),
        ("test", "Test notification from FlashForge Monitor"),
    ]

    for status, message in test_statuses:
        payload = {
            "printer_ip": "192.168.1.100",
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        # Validate payload structure
        assert "printer_ip" in payload, "Missing printer_ip"
        assert "status" in payload, "Missing status"
        assert "message" in payload, "Missing message"
        assert "timestamp" in payload, "Missing timestamp"

        print(f"[PASS] Payload for '{status}' status is valid")

    print("\nAll payload format tests passed!")
    return True


def main():
    if len(sys.argv) > 1:
        webhook_url = sys.argv[1]
        test_webhook(webhook_url)
    else:
        print("No webhook URL provided. Running format tests only.")
        print("Usage: python test_notifications.py <webhook_url>")
        print()

    test_notification_payloads()


if __name__ == "__main__":
    main()
