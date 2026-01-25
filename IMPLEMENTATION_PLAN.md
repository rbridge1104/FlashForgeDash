# Implementation Plan - FlashForge Adventurer 3 Monitor

## Project Goal
Create a local web-based dashboard to monitor and control a FlashForge Adventurer 3 3D printer. The system should be lightweight, easy to deploy locally, and provide real-time status updates.

## Architecture
*   **Backend:** Python (FastAPI). Handles printer communication (TCP), parses G-code, and serves the API.
*   **Frontend:** HTML/JS (No framework). Uses Tailwind CSS for styling. Polls the backend for status.
*   **Communication:**
    *   **Control:** TCP socket (port 8899) using FlashForge protocol.
    *   **Camera:** MJPEG stream (port 8080). Proxied through backend to avoid CORS issues.
    *   **Notifications:** Webhook (n8n).

## Completed Features
*   [x] **Basic Dashboard:** Status, temperatures, progress bar.
*   [x] **Printer Control:** Connect/Disconnect, Emergency Stop, LED Toggle, Pause/Resume.
*   [x] **Temperature Control:** Set nozzle and bed targets.
*   [x] **G-code Parsing:** Upload file to estimate print time.
*   [x] **File Management (v1.2.0):**
    *   Upload G-code to printer's SD card
    *   Upload and immediately start printing
    *   List files on printer
    *   Start printing existing files
    *   Delete files from printer
*   [x] **Configuration:** Edit printer IP and Webhook URL via UI.
*   [x] **Notifications:** Send status updates to n8n.
*   [x] **Security:** Bound to localhost, added CORS protection.
*   [x] **Camera Stream (v1.1.1):** MJPEG stream proxy working correctly.

## Version History
*   **v1.2.0** - Added file management (upload to printer, start print, list files, delete files)
*   **v1.1.1** - Fixed camera stream with proper session handling
*   **v1.1.0** - Initial release with basic features

## Future Enhancements
*   [ ] **Print History:** Log completed prints to a local database.
*   [ ] **Timelapse:** Capture snapshots from the camera stream at intervals.
*   [ ] **Multi-file Queue:** Queue multiple prints.