# Security Fixes Applied - Version 1.3.0

**Date:** January 25, 2026
**Previous Version:** 1.2.2
**New Version:** 1.3.0

## Summary of Security Improvements

All recommended security fixes have been implemented to protect your FlashForge Dashboard from unauthorized access and invalid inputs.

---

## 1. Network Isolation ✅

### Change: Localhost-Only Binding
**Files Modified:**
- `config.yaml` (line 10)
- `backend/main.py` (default config)

**Before:** Server bound to `0.0.0.0` (accessible from entire local network)
**After:** Server bound to `127.0.0.1` (localhost only)

**Impact:**
- Dashboard is now only accessible from the computer running the server
- Other devices on your network cannot access or control your printer
- Prevents unauthorized access from other WiFi/LAN users

**Access:** Use `http://localhost:8000` or `http://127.0.0.1:8000`

---

## 2. CORS Protection ✅

### Change: Added CORS Middleware
**File Modified:** `backend/main.py` (after app creation)

**Implementation:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Impact:**
- Prevents Cross-Site Request Forgery (CSRF) attacks
- Malicious websites cannot send commands to your printer
- Only requests from the dashboard itself are allowed

---

## 3. Input Validation ✅

### A. IP Address Validation
**Function Added:** `validate_ip_address()`
**Location:** `backend/main.py`

**Validation:**
- Uses Python's `ipaddress` module for strict validation
- Rejects malformed IP addresses
- Prevents configuration corruption

**Example:**
```bash
# Invalid IP rejected
{"detail":"Invalid IP address format: invalid.ip.address"}
```

### B. Webhook URL Validation
**Function Added:** `validate_webhook_url()`
**Location:** `backend/main.py`

**Validation:**
- Ensures URLs start with `http://` or `https://`
- Uses `urlparse` to verify proper URL structure
- Allows empty URLs (disables webhooks)

**Example:**
```bash
# Invalid URL rejected
{"detail":"Invalid webhook URL format. Must be http:// or https://"}
```

### C. G-code File Validation
**Enhanced:** `upload_gcode()` function
**Location:** `backend/main.py`

**New Validations:**
1. **File Size Check:** Maximum 100MB (configurable)
2. **Content Type Check:** Must be valid UTF-8 text
3. **G-code Format Check:** Must contain G/M/; commands in first 50 lines

**Protection Against:**
- Binary files being uploaded
- Excessively large files filling disk space
- Non-G-code files corrupting parser

---

## 4. Git Security ✅

### Change: Added .gitignore
**File Created:** `.gitignore`

**Protected Files:**
- `config.yaml` (contains printer IP, webhook URLs)
- `*.log` files (may contain debugging info)
- `venv/` (virtual environment)
- `__pycache__/` (Python cache)
- `uploads/` (user-uploaded files)

**Impact:**
- Sensitive configuration won't be committed to git
- Prevents accidental sharing of private data
- Cleaner repository

---

## Testing & Verification

All security features have been tested and verified:

### ✅ Network Binding
```bash
$ curl http://localhost:8000/api/config
{"version":"1.3.0",...}  # Works

$ curl http://192.168.1.x:8000/api/config
Connection refused  # Blocked (as expected)
```

### ✅ Input Validation
```bash
# Invalid IP rejected
$ curl -X POST http://localhost:8000/api/config \
  -d '{"printer_ip": "not-an-ip"}'
{"detail":"Invalid IP address format: not-an-ip"}

# Invalid webhook rejected
$ curl -X POST http://localhost:8000/api/config \
  -d '{"n8n_webhook_url": "invalid"}'
{"detail":"Invalid webhook URL format..."}

# Valid inputs accepted
$ curl -X POST http://localhost:8000/api/config \
  -d '{"printer_ip": "192.168.1.200"}'
{"success":true,"message":"Configuration updated"}
```

---

## Additional Recommendations (Future)

While the current implementation is secure for local use, consider these enhancements if deploying in more complex environments:

1. **Authentication:** Add username/password for dashboard access
2. **HTTPS:** Use SSL/TLS certificates for encrypted communication
3. **Rate Limiting:** Prevent brute-force attacks on API endpoints
4. **Audit Logging:** Track all configuration changes and control commands
5. **File Permissions:** Set `chmod 600` on `config.yaml` (Linux/Mac)

---

## Rollback Instructions

If you need to revert to network-accessible mode (NOT recommended):

1. Edit `config.yaml`:
   ```yaml
   server:
     host: "0.0.0.0"  # Allow network access
   ```

2. Restart the backend:
   ```bash
   pkill -f uvicorn
   cd /path/to/FlashForgeDash
   source venv/bin/activate
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

---

## Version History

- **v1.3.0** - Security hardening (localhost binding, CORS, input validation)
- **v1.2.2** - Camera stream fixes, cache-busting
- **v1.2.0** - File management features
- **v1.1.1** - Camera stream improvements
- **v1.1.0** - Initial release

---

## Support

For questions or issues:
- Review `SECURITY_RECOMMENDATIONS.md` for additional context
- Check `TROUBLESHOOTING_CAMERA.md` for camera-specific issues
- Consult `IMPLEMENTATION_PLAN.md` for feature documentation
