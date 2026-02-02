# FlashForgeDash

A lightweight, local web-based dashboard for monitoring and controlling FlashForge Adventurer 3 3D printers. Built with Python/FastAPI backend and a modern Tailwind CSS frontend.

## Features

- **Real-time Monitoring**
  - Live temperature gauges (nozzle and bed)
  - Print progress tracking with time remaining estimates
  - Connection status indicators
  - Real-time printer state updates (polling every 5 seconds)

- **Camera Stream**
  - Live MJPEG camera feed from printer
  - Backend proxy to avoid CORS issues
  - Fallback to direct camera link if proxy unavailable

- **Printer Control**
  - Emergency stop
  - Pause/Resume print jobs
  - LED light control
  - Temperature control (set nozzle and bed targets)

- **File Management**
  - Upload G-code files to printer's SD card
  - Upload and immediately start printing
  - List files on printer
  - Start printing existing files
  - Delete files from printer

- **G-code Analysis**
  - Parse G-code files to extract metadata
  - Estimated print time calculation
  - Filament usage estimation
  - Layer information

- **Notifications**
  - Webhook integration (n8n compatible)
  - Notifications on print completion
  - Error notifications
  - Configurable via dashboard

- **Security**
  - Localhost-only binding (127.0.0.1)
  - CORS protection
  - Input validation (IP addresses, webhook URLs, file uploads)
  - Configuration file excluded from git

## Installation

### Prerequisites

- Python 3.8 or higher
- FlashForge Adventurer 3 printer on your local network
- Printer IP address (find it in your printer's network settings)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/FlashForgeDash.git
   cd FlashForgeDash
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application:**
   ```bash
   cp config.yaml.example config.yaml
   ```
   
   Edit `config.yaml` and set your printer's IP address:
   ```yaml
   printer:
     ip_address: "192.168.1.200"  # Your printer's IP
   ```

5. **Start the server:**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

6. **Open the dashboard:**
   Open your browser and navigate to `http://localhost:8000`

## Configuration

The `config.yaml` file contains all configuration options:

```yaml
printer:
  ip_address: "192.168.1.200"  # Your printer's IP address
  control_port: 8899            # TCP control port (default: 8899)
  camera_port: 8080            # Camera stream port (default: 8080)
  poll_interval: 5             # Status polling interval in seconds

server:
  host: "127.0.0.1"            # localhost only for security
  port: 8000                    # Server port
  debug: false                  # Enable debug mode

notifications:
  n8n_webhook_url: ""          # Webhook URL for notifications
  notify_on_complete: true     # Notify when print completes
  notify_on_error: true         # Notify on printer errors

gcode:
  upload_directory: "./uploads" # Directory for uploaded files
  max_file_size_mb: 100        # Maximum file size in MB
```

### Security Configuration

By default, the server binds to `127.0.0.1` (localhost only) for security. This prevents other devices on your network from accessing the dashboard. If you need network access (not recommended), change the host to `0.0.0.0` in `config.yaml`.

## Usage

### Dashboard

The main dashboard provides:
- **Camera Feed**: Live view of your printer
- **Temperature Gauges**: Real-time nozzle and bed temperatures with target controls
- **Progress Bar**: Current print progress with time remaining
- **Control Buttons**: Emergency stop, LED control, pause/resume
- **File Management**: Upload, list, and manage files on printer
- **Settings**: Configure printer IP and webhook URL

### API Endpoints

The backend provides a REST API:

- `GET /api/status` - Get current printer status and telemetry
- `POST /api/control` - Send control commands (emergency_stop, led_on, led_off, pause, resume)
- `POST /api/temperature` - Set nozzle or bed temperature
- `POST /api/gcode/upload` - Upload and optionally start printing a G-code file
- `GET /api/files` - List files on printer's SD card
- `POST /api/files/print` - Start printing a file from SD card
- `POST /api/files/delete` - Delete a file from SD card
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration
- `GET /api/camera/stream` - Camera stream proxy endpoint
- `POST /api/reconnect` - Force reconnection to printer

### Example API Usage

```bash
# Get printer status
curl http://localhost:8000/api/status

# Emergency stop
curl -X POST http://localhost:8000/api/control \
  -H "Content-Type: application/json" \
  -d '{"command": "emergency_stop"}'

# Set nozzle temperature
curl -X POST http://localhost:8000/api/temperature \
  -H "Content-Type: application/json" \
  -d '{"target": "nozzle", "temperature": 210}'
```

## Architecture

- **Backend**: Python (FastAPI)
  - Handles printer communication via TCP socket (port 8899)
  - Parses G-code files for metadata
  - Serves REST API and static files
  - Proxies camera stream to avoid CORS issues

- **Frontend**: HTML/JavaScript (no framework)
  - Tailwind CSS for styling
  - Polls backend API every 5 seconds
  - Real-time dashboard updates

- **Communication**:
  - **Control**: TCP socket (port 8899) using FlashForge protocol
  - **Camera**: MJPEG stream (port 8080) proxied through backend
  - **Notifications**: HTTP webhooks (n8n compatible)

## Security Features

FlashForgeDash includes several security measures for safe local operation:

### Network Isolation
- Server binds to `127.0.0.1` by default (localhost only)
- Prevents unauthorized network access
- Dashboard only accessible from the host machine

### CORS Protection
- CORS middleware restricts requests to localhost origins only
- Prevents CSRF attacks from malicious websites
- Only allows requests from the dashboard itself

### Input Validation
- **IP Address Validation**: Uses Python's `ipaddress` module to validate printer IPs
- **Webhook URL Validation**: Ensures URLs are properly formatted (http:// or https://)
- **File Upload Validation**: 
  - File size limits (100MB default, configurable)
  - Content type validation (UTF-8 text)
  - G-code format verification

### Git Security
- `config.yaml` is excluded from git (contains sensitive data)
- Log files excluded
- Virtual environment excluded

## Troubleshooting

### Camera Stream Issues

**Problem**: Camera feed shows "Camera unavailable"

**Solutions**:
1. **Check camera is enabled**: Verify camera is enabled in printer settings
2. **Test direct access**: Open `http://[PRINTER_IP]:8080/?action=stream` in browser
   - If this works, the camera is functioning
   - If not, the camera may be disabled or the printer needs a restart
3. **Connection limit (MOST COMMON)**: FlashForge cameras only allow ONE connection at a time
   - Close any other browser tabs accessing the camera directly
   - Close other applications using the camera (OctoPrint, slicer software, etc.)
   - Refresh the dashboard after closing other connections
4. **Network issues**: 
   - Ensure printer is on the same network
   - Check firewall isn't blocking port 8080
   - Verify printer is reachable: `ping [PRINTER_IP]`

**Error**: "Connection aborted" or "Remote end closed connection"
- The printer's camera service stopped responding
- Another application is using the camera
- Printer was rebooted or camera disabled
- **Solution**: Use the "Open direct camera link in new tab" button as a fallback

### Printer Connection Issues

**Problem**: Dashboard shows "Disconnected"

**Solutions**:
1. Verify printer IP address in `config.yaml` is correct
2. Check printer is powered on and connected to network
3. Test TCP connection: `telnet [PRINTER_IP] 8899` (should connect)
4. Use the reconnect button in dashboard settings
5. Check firewall isn't blocking port 8899

### File Upload Issues

**Problem**: File upload fails

**Solutions**:
1. Check file size is under the limit (100MB default)
2. Verify file is a valid G-code file (.gcode, .gco, .g extension)
3. Ensure printer is connected and has space on SD card
4. Check backend logs for specific error messages

## Version History

- **v1.3.0** - Security hardening (localhost binding, CORS, input validation)
- **v1.2.2** - Camera stream fixes, cache-busting
- **v1.2.0** - File management features (upload, list, delete, start print)
- **v1.1.1** - Camera stream improvements and fixes
- **v1.1.0** - Initial release with basic monitoring and control

## Future Enhancements

- [ ] Print History: Log completed prints to a local database
- [ ] Timelapse: Capture snapshots from camera stream at intervals
- [ ] Multi-file Queue: Queue multiple prints for sequential execution
- [ ] Print Statistics: Track print success rates and filament usage
- [ ] Mobile-friendly UI improvements

## Technical Details

### FlashForge Protocol

The application communicates with the printer using the FlashForge protocol over TCP port 8899:

- **Handshake**: `~M601 S1` - Establishes connection
- **Temperature Query**: `~M105` - Returns current and target temperatures
- **Status Query**: `~M119` - Returns printer status (idle, printing, paused, etc.)
- **Emergency Stop**: `~M112` - Immediately stops all operations
- **LED Control**: `~M146 r<val> g<val> b<val> F<freq>` - Controls LED light
- **Pause/Resume**: `~M25` (pause), `~M24` (resume)
- **Temperature Set**: `~M104 S<temp>` (nozzle), `~M140 S<temp>` (bed)
- **File Operations**: `~M20` (list), `~M23` (select), `~M30` (delete), `~M28`/`~M29` (upload)

### G-code Parsing

The G-code parser extracts metadata from Orca Slicer and PrusaSlicer G-code files:
- Estimated printing time
- Filament usage (mm and grams)
- Layer height and count
- Temperature settings

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

[Add your license here - MIT, Apache 2.0, etc.]

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Note**: This software is designed for local use only. The default configuration binds to localhost for security. Do not expose this application to the internet without additional security measures (authentication, HTTPS, etc.).
