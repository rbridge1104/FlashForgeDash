# Security Uplift Recommendations for FlashForgeDash (Local Deployment)

This document outlines recommended security improvements for running the FlashForgeDash application in a local, non-production environment. The goal is to prevent accidental exposure and ensure stable operation without the complexity of enterprise-grade security.

## 1. Network Isolation

### Recommendation: Bind to Localhost
**Current Status:** The application listens on `0.0.0.0` (all network interfaces), making the dashboard accessible to anyone on your local network (Wi-Fi/LAN).
**Fix:** Change the default host in `backend/main.py` and `config.yaml` to `127.0.0.1`.
**Impact:** Only the computer running the software can access the dashboard.

### Recommendation: Strict CORS Policy
**Current Status:** No CORS middleware is configured. While modern browsers have protections, an explicit policy is safer.
**Fix:** Configure FastAPI's `CORSMiddleware` to allow origins only from `http://127.0.0.1:8000` and `http://localhost:8000`.
**Impact:** Prevents malicious websites visited in your browser from sending commands to your printer in the background (CSRF-like attacks).

## 2. Input Validation & Stability

### Recommendation: IP Address Validation
**Current Status:** The `/api/config` endpoint accepts any string as an IP address. A typo or malicious input could break the connection logic or potentially cause SSRF if the client logic were different.
**Fix:** Implement a regular expression or use Python's `ipaddress` module to validate the `printer_ip` before accepting updates.
**Impact:** Prevents configuration corruption and simple injection attempts.

### Recommendation: Webhook URL Validation
**Current Status:** Any string is accepted as a webhook URL.
**Fix:** Ensure the `n8n_webhook_url` starts with `http://` or `https://`.
**Impact:** Prevents invalid configurations that would cause the notification system to fail.

### Recommendation: G-code File Checks
**Current Status:** The upload endpoint only checks file extensions.
**Fix:** While full parsing is resource-intensive, a quick check of the first few bytes (magic number or header) to ensure it looks like a text file is a low-cost safety measure.
**Impact:** Prevents uploading binary files or scripts that might confuse the parser or fill up disk space.

## 3. Configuration Security

### Recommendation: Configuration File Permissions
**Current Status:** `config.yaml` contains the printer IP and potentially sensitive webhook URLs.
**Fix:** Ensure `config.yaml` is readable/writable only by the user running the application (`chmod 600 config.yaml` on Linux/Mac).
**Impact:** Prevents other users on the same machine (if any) from reading your configuration.

### Recommendation: Sanitize API Outputs
**Current Status:** The `/api/config` endpoint returns the webhook URL.
**Fix:** Mask the webhook URL in the API response (e.g., `https://n8n.example.com/...`) if it contains sensitive tokens.
**Impact:** Prevents accidental leakage of the webhook URL if you screen-share or take a screenshot of the developer console.

## 4. Printer Communication

### Recommendation: Connection Timeout Handling
**Current Status:** The application connects to the printer via raw TCP.
**Fix:** Ensure all socket operations have strict timeouts. If the printer hangs or a network issue occurs, the backend should not freeze indefinitely.
**Impact:** Improves application reliability and responsiveness.

## Summary of Immediate Actions

1.  **Modify `backend/main.py`** to listen on `127.0.0.1` by default.
2.  **Add `CORSMiddleware`** to `backend/main.py`.
3.  **Add Input Validation** to the `update_config` function in `backend/main.py`.
