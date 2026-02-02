# FlashForgeDash

A modern, secure web dashboard for monitoring and controlling FlashForge Adventurer 3 3D printers. Built with Python/FastAPI backend and a beautiful Tailwind CSS frontend with Google OAuth authentication.

![Version](https://img.shields.io/badge/version-1.3.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

### 🔐 Authentication & Security
- **Google OAuth Integration** - Secure sign-in with Google accounts
- **Admin Approval System** - Control who can access your printer dashboard
- **Session Management** - Secure cookie-based sessions with automatic expiration
- **Localhost Binding** - Server only accessible from your machine by default
- **CORS Protection** - Prevents unauthorized cross-origin requests
- **Input Validation** - Comprehensive validation for all user inputs

### 📊 Real-time Monitoring
- **Live Temperature Tracking** - Real-time nozzle and bed temperature gauges with visual indicators
- **Print Progress** - Live progress bar with accurate time remaining estimates
- **Connection Status** - Visual indicators for printer connectivity
- **Printer Position** - Real-time X, Y, Z axis position tracking
- **Auto-refresh** - Dashboard updates every 2 seconds

### 🎥 Camera Integration
- **Live MJPEG Stream** - Real-time camera feed from your printer
- **Snapshot Capture** - Save still images during prints
- **Fullscreen Mode** - View camera feed in fullscreen
- **Backend Proxy** - Avoids CORS issues with direct camera access

### 🎮 Printer Control
- **Emergency Stop** - Immediate halt of all printer operations
- **Print Controls** - Pause, resume, and cancel prints with VCR-style buttons
- **Temperature Management** - Set custom nozzle and bed temperatures
- **Material Presets** - One-click temperature presets for PLA, PETG, ABS, ASA
- **LED Control** - Toggle printer LED lighting
- **Fan Control** - Control cooling fan
- **Home Axes** - Return print head to home position

### 📁 File Management
- **G-code Upload** - Drag-and-drop or click to upload files (up to 100MB)
- **File Validation** - Automatic validation of G-code files
- **G-code Parsing** - Extract metadata (print time, filament usage, layers)
- **Start Printing** - Upload and immediately start printing
- **SD Card Management** - List, select, and delete files on printer

### 🔔 Notifications
- **Webhook Integration** - Send notifications via n8n or other webhook services
- **Print Completion** - Get notified when prints finish
- **Error Alerts** - Receive alerts for printer errors
- **Test Functionality** - Test webhook integration from settings

### ⚙️ Configuration
- **Dynamic Settings** - Update printer IP and settings without restart
- **Material Presets** - Customize temperature presets for different materials
- **Network Scanner** - Automatically find FlashForge printers on your network
- **Admin Dashboard** - Manage user access requests (admin only)

## 📋 Prerequisites

- **Python 3.8 or higher**
- **FlashForge Adventurer 3** printer on your local network
- **Google Cloud Account** (for OAuth - free tier is sufficient)
- **Printer IP Address** (find in printer's network settings)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/FlashForgeDash.git
cd FlashForgeDash
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Google OAuth

#### Create OAuth Credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure OAuth consent screen if prompted:
   - User Type: **External** (unless you have a workspace)
   - App name: **FlashForge Dashboard**
   - User support email: Your email
   - Developer contact: Your email
6. For Application type, select **Web application**
7. Add authorized redirect URIs:
   ```
   http://localhost:8000/auth/callback
   http://127.0.0.1:8000/auth/callback
   ```
8. Click **Create**
9. Copy the **Client ID** and **Client Secret**

#### Configure Environment Variables:

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OAuth credentials:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here

# Session Security
SESSION_SECRET_KEY=your-random-secret-key-here

# Admin Configuration
ADMIN_EMAILS=your-email@gmail.com,other-admin@gmail.com

# Server Configuration (optional)
APP_HOST=127.0.0.1
APP_PORT=8000
```

**Important**:
- Replace `your-client-id-here` and `your-client-secret-here` with your actual Google OAuth credentials
- Generate a secure `SESSION_SECRET_KEY` (e.g., `openssl rand -hex 32`)
- Add your Gmail address to `ADMIN_EMAILS` to become the first admin

### 5. Configure Printer Settings

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` and set your printer's IP address:

```yaml
printer:
  ip_address: "192.168.1.200"  # Replace with your printer's IP
  control_port: 8899
  camera_port: 8080
  poll_interval: 5

server:
  host: "127.0.0.1"  # localhost only (recommended)
  port: 8000
  debug: false

notifications:
  n8n_webhook_url: ""  # Optional: Add webhook URL for notifications
  notify_on_complete: true
  notify_on_error: true

material_presets:
  pla:
    nozzle: 200
    bed: 60
  petg:
    nozzle: 235
    bed: 80
  abs:
    nozzle: 230
    bed: 100
  asa:
    nozzle: 240
    bed: 100

gcode:
  max_file_size_mb: 100
```

### 6. Start the Server

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Or with auto-reload during development:

```bash
uvicorn backend.main:app --reload
```

### 7. Access the Dashboard

1. Open your browser and navigate to: `http://localhost:8000`
2. Click **Sign in with Google**
3. Authenticate with your Google account
4. If you're an admin (listed in `ADMIN_EMAILS`), you'll have immediate access
5. If not an admin, your access will be pending until an admin approves

## 🔧 Configuration Guide

### Printer Configuration

Find your printer's IP address:
- On the printer, go to: **Settings** → **Network** → **Network Info**
- Or use the built-in network scanner in Settings page (admin only)

Update `config.yaml` with the IP address.

### Admin Management

**Becoming an Admin:**
- Add your email to the `ADMIN_EMAILS` environment variable in `.env`
- Restart the server
- Sign in with that Google account

**Approving Users (Admin Only):**
1. Navigate to Settings page (gear icon in header)
2. View pending access requests
3. Click **Approve** or **Deny** for each request
4. Users receive immediate access after approval

### Webhook Notifications

To receive notifications (e.g., when prints complete):

1. Set up an n8n instance or any webhook receiver
2. Add the webhook URL to `config.yaml`:
   ```yaml
   notifications:
     n8n_webhook_url: "https://your-n8n-instance.com/webhook/printer"
   ```
3. Test the webhook in Settings → **Send Test Notification**

Notification payload example:
```json
{
  "printer_ip": "192.168.1.200",
  "status": "complete",
  "message": "Print job completed successfully!",
  "timestamp": "2024-02-01T12:34:56.789Z"
}
```

## 📖 Usage Guide

### Dashboard Overview

The dashboard is organized into cards:

1. **Printer Status** (Top Left)
   - Current status (Idle, Printing, Paused, Complete, Error)
   - VCR-style controls (Play/Pause/Stop)
   - Printer position (X, Y, Z)
   - Quick controls (Home, LED, Fan)

2. **Temperatures** (Top Right)
   - Real-time nozzle and bed temperatures
   - Set target temperatures
   - Material presets (PLA, PETG, ABS, ASA)
   - Cool Down All button

3. **Print Progress** (Bottom Left)
   - Progress percentage
   - Time remaining
   - Current file name
   - Layer information

4. **Live Feed** (Bottom Right)
   - Real-time camera stream
   - Snapshot capture
   - Fullscreen mode

5. **File Management** (Full Width)
   - Upload G-code files
   - Drag-and-drop support
   - Start print button

### Uploading and Printing

**Method 1: Upload and Print Later**
1. Drag a `.gcode` file onto the upload zone or click to browse
2. Wait for upload confirmation
3. Click **START PRINT** to begin printing

**Method 2: Print from Uploaded File**
1. Upload file as above
2. File metadata is parsed automatically
3. Use the START PRINT button to begin

### Temperature Presets

Quick temperature presets for common materials:
- **PLA**: 200°C nozzle, 60°C bed
- **PETG**: 235°C nozzle, 80°C bed
- **ABS**: 230°C nozzle, 100°C bed
- **ASA**: 240°C nozzle, 100°C bed

Customize these in `config.yaml` under `material_presets`.

### Emergency Stop

The red **STOP** sign in the header immediately halts all printer operations:
- Stops all movement
- Disables heaters
- Requires printer restart to resume

**Use only in emergencies!**

## 🔌 API Reference

The backend provides a RESTful API (requires authentication):

### Status & Monitoring
- `GET /api/status` - Get current printer status and telemetry
- `GET /api/position` - Get current X/Y/Z position
- `GET /api/config` - Get current configuration (sensitive data masked)
- `GET /api/config/full` - Get full configuration (admin only)

### Printer Control
- `POST /api/control` - Send control commands
  ```json
  { "command": "emergency_stop" | "led_on" | "led_off" | "pause" | "resume" | "fan_on" | "fan_off" | "disable_motors" | "home_axes" }
  ```
- `POST /api/temperature` - Set temperature
  ```json
  { "target": "nozzle" | "bed", "temperature": 200 }
  ```
- `POST /api/reconnect` - Force reconnection to printer

### File Management
- `POST /api/gcode/upload` - Upload G-code file (multipart/form-data)
  - `file`: G-code file
  - `upload_to_printer`: boolean (optional)
  - `start_print`: boolean (optional)
- `GET /api/files` - List files on printer's SD card
- `POST /api/files/print` - Start printing a file
  ```json
  { "filename": "model.gcode" }
  ```
- `POST /api/files/delete` - Delete file from printer
  ```json
  { "filename": "model.gcode" }
  ```

### Configuration (Admin Only)
- `POST /api/config` - Update basic configuration
- `POST /api/config/full` - Update full configuration
- `POST /api/scan-network` - Scan for FlashForge printers on network

### Camera
- `GET /api/camera` - Get camera URLs
- `GET /api/camera/stream` - Proxy MJPEG stream

### Notifications
- `POST /api/notifications/test` - Send test notification

### Authentication
- `GET /auth/login` - Initiate Google OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `POST /auth/logout` - Sign out
- `GET /auth/status` - Get authentication status
- `GET /auth/activate` - Activate pending user after approval

### Admin (Admin Only)
- `GET /api/admin/requests` - Get pending access requests
- `POST /api/admin/approve` - Approve user access
  ```json
  { "email": "user@example.com" }
  ```
- `POST /api/admin/deny` - Deny user access
  ```json
  { "email": "user@example.com" }
  ```

## 🛠️ Troubleshooting

### Authentication Issues

**Problem**: "Access Pending" after sign-in

**Solution**:
- You need admin approval to access the dashboard
- Contact the admin to approve your email address
- Or add your email to `ADMIN_EMAILS` in `.env` and restart

**Problem**: OAuth error "redirect_uri_mismatch"

**Solution**:
- Check authorized redirect URIs in Google Cloud Console
- Must include: `http://localhost:8000/auth/callback`
- Make sure the port matches your server configuration

### Camera Issues

**Problem**: Camera shows "Unavailable"

**Solutions**:
1. **Single Connection Limit**: FlashForge cameras only allow ONE connection
   - Close other browser tabs with camera feed
   - Close OctoPrint, slicer, or other software using camera
   - Refresh dashboard after closing connections

2. **Check Camera Access**: Open `http://[PRINTER_IP]:8080/?action=stream` directly
   - If this works, camera is functional
   - If not, check printer camera settings or restart printer

3. **Network Issues**:
   - Verify printer on same network
   - Check firewall isn't blocking port 8080
   - Test connectivity: `ping [PRINTER_IP]`

### Printer Connection Issues

**Problem**: Dashboard shows "Disconnected"

**Solutions**:
1. Verify printer IP in `config.yaml` is correct
2. Ensure printer is powered on and connected to network
3. Test connection: `telnet [PRINTER_IP] 8899` (should connect)
4. Use **Reconnect** button in dashboard
5. Check firewall isn't blocking port 8899
6. Restart printer if connection continues to fail

### File Upload Issues

**Problem**: Upload fails or shows error

**Solutions**:
1. Check file size is under limit (100MB default)
2. Verify file extension is `.gcode`, `.gco`, or `.g`
3. Ensure file contains valid G-code commands
4. Check printer is connected
5. Verify SD card has sufficient space
6. Review browser console for specific errors

### Performance Issues

**Problem**: Dashboard is slow or unresponsive

**Solutions**:
1. Reduce `poll_interval` in `config.yaml` (default: 5 seconds)
2. Close camera stream if not needed
3. Check server resources (CPU/memory)
4. Restart the server

## 🏗️ Architecture

### Technology Stack

**Backend:**
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **httpx** - Async HTTP client for OAuth
- **Authlib** - OAuth 2.0 implementation
- **PyYAML** - Configuration management

**Frontend:**
- **Vanilla JavaScript** - No framework dependencies
- **Tailwind CSS** - Utility-first styling
- **Fetch API** - Native HTTP requests

### Communication Protocols

**Printer Control:**
- Protocol: TCP socket on port 8899
- Commands: FlashForge proprietary protocol
- Format: `~M[code] [parameters]\r\n`

**Camera Stream:**
- Protocol: MJPEG over HTTP on port 8080
- Proxied through backend to avoid CORS
- Single connection limitation

**Notifications:**
- Protocol: HTTP POST webhooks
- Format: JSON payload
- Compatible with n8n, Zapier, IFTTT, etc.

### Security Architecture

1. **Authentication Layer**
   - OAuth 2.0 with Google
   - Session-based access control
   - Admin approval system

2. **Network Security**
   - Localhost binding (127.0.0.1)
   - CORS protection
   - No external exposure

3. **Data Validation**
   - IP address validation
   - URL validation
   - File upload validation
   - Size limits enforced

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_gcode_parser.py

# Run with coverage
pytest --cov=backend tests/
```

### Development Mode

Start server with auto-reload:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Project Structure

```
FlashForgeDash/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── printer_client.py    # Printer communication
│   ├── gcode_parser.py      # G-code metadata extraction
│   ├── auth.py              # OAuth implementation
│   ├── user_store.py        # User access management
│   └── session_store.py     # Session management
├── frontend/
│   ├── index.html           # Main dashboard
│   ├── login.html           # Login page
│   ├── settings.html        # Settings page (admin)
│   ├── pending.html         # Access pending page
│   └── static/              # Static assets
├── tests/
│   ├── test_gcode_parser.py
│   ├── test_notifications.py
│   └── test_socket.py
├── data/
│   └── users.json           # User access data
├── .env                     # Environment variables (create from .env.example)
├── config.yaml              # Printer configuration (create from .yaml.example)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 📝 Version History

- **v1.3.0** (Current)
  - Added Google OAuth authentication
  - Admin approval system for user access
  - Material temperature presets
  - File upload with drag-and-drop
  - Camera fullscreen mode
  - Network printer scanner
  - Security hardening (CORS, validation, localhost binding)

- **v1.2.2**
  - Camera stream improvements
  - Cache-busting for static assets

- **v1.2.0**
  - File management features
  - Upload, list, delete G-code files
  - Start printing from dashboard

- **v1.1.0**
  - Initial release
  - Basic monitoring and control

## 🎯 Future Enhancements

- [ ] Print history and statistics database
- [ ] Timelapse video creation from snapshots
- [ ] Multi-printer support
- [ ] Print queue management
- [ ] Filament usage tracking
- [ ] Email notifications option
- [ ] Mobile app (React Native)
- [ ] Raspberry Pi installation guide
- [ ] Docker containerization

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows existing style
- All tests pass
- New features include tests
- Documentation is updated

## 📄 License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2024 FlashForgeDash Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ⚠️ Disclaimer

**This software is designed for local use only.** The default configuration binds to localhost (127.0.0.1) for security.

**Do not expose this application to the internet** without implementing additional security measures:
- Reverse proxy with HTTPS (nginx, Caddy)
- Additional authentication layers
- Rate limiting
- Firewall rules
- Regular security updates

The authors are not responsible for any damage to your printer, failed prints, or security issues arising from improper configuration or use.

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/FlashForgeDash/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/FlashForgeDash/discussions)
- **Email**: [your-email@example.com]

## 🙏 Acknowledgments

- FlashForge for their 3D printer technology
- FastAPI team for the excellent framework
- Tailwind CSS for the beautiful styling system
- The 3D printing community for inspiration and support

---

**Made with ❤️ for the 3D printing community**
