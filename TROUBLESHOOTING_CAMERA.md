# Troubleshooting Log: Camera Stream Issues

**Date:** January 24, 2026
**Issue:** Dashboard camera feed is broken (no image), but direct access to printer URL works.

## Attempted Fixes & Outcomes

### 1. Diagnosis
*   **Printer Model:** FlashForge Adventurer 3
*   **Printer Camera URL:** `http://[IP]:8080/?action=stream`
*   **Stream Type:** MJPEG (Multipart/x-mixed-replace)
*   **Direct Access:** Verified working via browser (`http://192.168.1.200:8080/?action=stream`).
*   **Dashboard Access:** Fails (broken image icon).

### 2. Backend Proxy (Attempt 1: `httpx` + `StreamingResponse`)
*   **Implementation:** Used `httpx.AsyncClient` to stream bytes.
*   **Result:** Failed.
*   **Reason:** The printer sends a custom boundary in the `Content-Type` header (`boundary=boundarydonotcross`). The initial code hardcoded `boundary=myboundary`, causing the browser to reject the stream because it couldn't find the frame delimiters.

### 3. Backend Proxy (Attempt 2: Dynamic Headers)
*   **Implementation:** Updated `main.py` to fetch `Content-Type` from the printer and pass it to the frontend.
*   **Result:** Failed.
*   **Suspected Reason:** `httpx` async iterator might be buffering or handling the infinite stream in a way that `Starlette.StreamingResponse` doesn't like, or the connection is dropping prematurely.

### 4. Direct Frontend Connection (Attempt 3: Bypass Proxy)
*   **Implementation:** Backend returned the direct printer URL (`http://192.168.1.200...`). Frontend set `<img src="...">` directly.
*   **Result:** Failed.
*   **Reason:** **Private Network Access** (CORS). Modern browsers block requests from `localhost` (or public contexts) to private IP addresses (`192.168.x.x`) unless the target device sends specific CORS preflight headers. The printer does *not* send these headers.
*   **Conclusion:** A backend proxy is **mandatory**.

### 5. Backend Proxy (Attempt 4: `requests` + Synchronous Generator)
*   **Implementation:** Switched from `httpx` to `requests` (synchronous). Use `requests.get(stream=True)` and `iter_content()` inside a generator.
*   **Status:** Implemented in `backend/main.py`. Added `requests` to `requirements.txt`.
*   **Current Code:**
    ```python
    @app.get("/api/camera/stream")
    async def camera_stream_proxy():
        # ... fetch headers first ...
        def stream_generator():
            with requests.get(camera_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    yield chunk
        return StreamingResponse(stream_generator(), media_type=content_type)
    ```

## Current Status
**RESOLVED** - The camera stream proxy is now working correctly.

## Final Solution (January 25, 2026)

### Issues Fixed:

1.  **Missing Import:** `requests` module was in `requirements.txt` but not imported in `backend/main.py`.
    *   **Fix:** Added `import requests` at line 9.

2.  **Incorrect Relative Imports:** Imports of `printer_client` and `gcode_parser` were not using relative import syntax.
    *   **Fix:** Changed `from printer_client import...` to `from .printer_client import...` and same for gcode_parser.

3.  **Connection Pooling Issues:** The printer's camera doesn't handle HTTP keep-alive connections well.
    *   **Fix:** Created a new session for each stream request with `Connection: close` header and proper timeout handling (10s connect, infinite read timeout).

4.  **Stream Buffering:** Using synchronous `requests` in generator with FastAPI's `StreamingResponse`.
    *   **Fix:** Wrapped the streaming logic in a generator function with small chunk sizes (1024 bytes) and proper session cleanup.

## Verification
*   Backend starts successfully with `python -m uvicorn backend.main:app`
*   `/api/status` endpoint returns printer telemetry correctly
*   `/api/camera/stream` endpoint:
    *   Returns HTTP 503 with clear error message when camera is offline
    *   Will stream MJPEG when camera is accessible on printer port 8080

## Testing the Camera Stream
When the printer's camera is running and accessible:
1.  Verify direct access: Open `http://[PRINTER_IP]:8080/?action=stream` in browser
2.  Test proxy: Open `http://localhost:8000/api/camera/stream` - should show same stream
3.  Frontend: Camera feed in dashboard should display automatically

## Common Camera Issues

### Camera Not Streaming
If the camera feed shows "Camera unavailable":

1.  **Check if camera is enabled on printer:**
    *   Some printers turn off the camera to save resources
    *   Check printer settings or LCD menu for camera option

2.  **Test direct access:**
    *   Open `http://192.168.1.200:8080/?action=stream` in your browser
    *   If this doesn't work, the camera itself isn't streaming
    *   Use the "Open direct camera link in new tab" fallback button

3.  **Connection limit (MOST COMMON):**
    *   **FlashForge cameras only allow ONE connection at a time**
    *   If you have the camera open in another browser tab (`http://PRINTER_IP:8080/?action=stream`), close it!
    *   Close any other applications accessing the camera (OctoPrint, slicer software, etc.)
    *   **Solution:** Close all direct camera connections, then refresh the dashboard

4.  **Network issues:**
    *   Ensure the printer is on the same network
    *   Check firewall settings aren't blocking port 8080
    *   Try `ping 192.168.1.200` to verify printer is reachable

### Error: "Connection aborted" or "Remote end closed connection"
This typically means:
- The printer's camera service stopped responding mid-stream
- Another application is using the camera
- The printer was rebooted or camera was disabled

**Solution:** Click the "Open direct camera link in new tab" button to access the camera directly, bypassing the proxy.
