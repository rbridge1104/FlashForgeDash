"""
FlashForge Adventurer 3 Monitor - FastAPI Backend

Provides REST API for printer status, control, and notifications.
"""

import os
import asyncio
import httpx
import requests
import yaml
import re
import ipaddress
from pathlib import Path
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from starlette.middleware.sessions import SessionMiddleware

from .printer_client import PrinterClient, PrinterState, PrinterStatus
from .gcode_parser import GCodeParser, GCodeMetadata
from . import auth
from .user_store import user_store

# Load environment variables
load_dotenv()

VERSION = "1.3.0"

# Load configuration
def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {
            "printer": {"ip_address": "192.168.1.100", "poll_interval": 5},
            "server": {"host": "127.0.0.1", "port": 8000},
            "notifications": {"n8n_webhook_url": "", "notify_on_complete": True},
        }

    # Override with environment variables
    if os.getenv("PRINTER_IP"):
        config["printer"]["ip_address"] = os.getenv("PRINTER_IP")

    if os.getenv("PRINTER_POLL_INTERVAL"):
        try:
            config["printer"]["poll_interval"] = int(os.getenv("PRINTER_POLL_INTERVAL"))
        except ValueError:
            pass

    if os.getenv("N8N_WEBHOOK_URL"):
        config["notifications"]["n8n_webhook_url"] = os.getenv("N8N_WEBHOOK_URL")

    if os.getenv("APP_HOST"):
        config["server"]["host"] = os.getenv("APP_HOST")

    if os.getenv("APP_PORT"):
        try:
            config["server"]["port"] = int(os.getenv("APP_PORT"))
        except ValueError:
            pass

    return config


def validate_ip_address(ip: str) -> bool:
    """Validate IP address format."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL format."""
    if not url:
        return True  # Empty URL is valid (disables webhooks)
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


config = load_config()

# Global state
printer_client: Optional[PrinterClient] = None
current_gcode_metadata: Optional[GCodeMetadata] = None
print_start_time: Optional[datetime] = None
last_status: Optional[PrinterStatus] = None


async def send_notification(status: str, message: str) -> None:
    """Send notification to n8n webhook."""
    webhook_url = config.get("notifications", {}).get("n8n_webhook_url", "")
    if not webhook_url:
        return

    payload = {
        "printer_ip": config["printer"]["ip_address"],
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Failed to send notification: {e}")


def status_change_callback(state: PrinterState) -> None:
    """Callback for printer status changes."""
    global last_status

    if last_status != state.status:
        if state.status == PrinterStatus.COMPLETE:
            if config.get("notifications", {}).get("notify_on_complete", True):
                asyncio.create_task(send_notification(
                    "complete",
                    "Print job completed successfully!"
                ))
        elif state.status == PrinterStatus.ERROR:
            if config.get("notifications", {}).get("notify_on_error", True):
                asyncio.create_task(send_notification(
                    "error",
                    f"Printer error: {state.error_message}"
                ))
        last_status = state.status


def try_connect_printer():
    """Try to connect to printer in background thread."""
    global printer_client
    try:
        if printer_client and printer_client.connect():
            printer_client.add_status_callback(status_change_callback)
            printer_client.start_polling()
            print(f"Connected to printer at {config['printer']['ip_address']}")
    except Exception as e:
        print(f"Warning: Could not connect to printer: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage printer connection lifecycle."""
    global printer_client

    printer_ip = config["printer"]["ip_address"]
    printer_client = PrinterClient(printer_ip)

    # Try to connect in background thread (non-blocking)
    import threading
    connect_thread = threading.Thread(target=try_connect_printer, daemon=True)
    connect_thread.start()

    yield

    # Cleanup
    if printer_client:
        printer_client.disconnect()


app = FastAPI(
    title="FlashForge Monitor",
    description="Dashboard and API for FlashForge Adventurer 3",
    version="1.0.0",
    lifespan=lifespan
)

# Configure OAuth
oauth_configured = auth.configure_oauth()
if oauth_configured:
    print("✓ OAuth configured successfully")
else:
    print("⚠ OAuth not configured - running without authentication")

# Add Session middleware (required for OAuth)
secret_key = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=secret_key, session_cookie="_oauth_state")

# Add CORS middleware for security
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

# Mount static files
static_path = Path(__file__).parent.parent / "frontend" / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Pydantic models for API
class StatusResponse(BaseModel):
    connected: bool
    status: str
    nozzle_temp: float
    nozzle_target: float
    bed_temp: float
    bed_target: float
    progress: int
    led_on: bool
    time_remaining_seconds: int
    time_remaining_formatted: str
    gcode_filename: Optional[str] = None


class ControlCommand(BaseModel):
    command: str  # "emergency_stop", "led_on", "led_off", "pause", "resume"


class ConfigUpdate(BaseModel):
    printer_ip: Optional[str] = None
    n8n_webhook_url: Optional[str] = None


class NotificationPayload(BaseModel):
    status: str
    message: str


# Authentication Routes

@app.get("/auth/login")
async def login(request: Request):
    """Initiate OAuth login flow."""
    return await auth.handle_login(request)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback from Google."""
    return await auth.handle_callback(request)


@app.post("/auth/logout")
async def logout(request: Request):
    """Logout and clear session."""
    return await auth.handle_logout(request)


@app.get("/auth/status")
async def auth_status(request: Request):
    """Get current authentication status."""
    return await auth.get_auth_status(request)


@app.get("/auth/activate")
async def activate_access(request: Request):
    """Activate a pending user's session after admin approval."""
    email = auth.get_pending_email(request)

    if not email:
        return RedirectResponse("/login.html")

    # Check if user is now approved
    if not user_store.is_approved(email):
        # Still pending or denied
        return RedirectResponse("/pending.html")

    # User is approved - redirect to dashboard (session already exists from callback)
    print(f"Activated approved user: {email}")
    return RedirectResponse("/")


@app.get("/api/auth/pending-status")
async def get_pending_status(request: Request):
    """Check if a pending user has been approved or denied."""
    email = auth.get_pending_email(request)

    if not email:
        return {"status": "unknown"}

    if user_store.is_approved(email):
        return {"status": "approved", "email": email}
    elif email.lower() in [e.lower() for e in user_store._data.get("denied", [])]:
        return {"status": "denied", "email": email}
    else:
        return {"status": "pending", "email": email}


@app.get("/api/admin/requests")
async def get_pending_requests(request: Request):
    """Get list of pending access requests (admin only)."""
    if not auth.is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    pending = user_store.get_pending_requests()
    return {"pending": pending}


@app.post("/api/admin/approve")
async def approve_user(request: Request):
    """Approve a pending access request (admin only)."""
    if not auth.is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    data = await request.json()
    email = data.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    success = user_store.approve(email)

    if success:
        print(f"Admin approved access for: {email}")
        return {"success": True, "message": f"Approved {email}"}
    else:
        return {"success": False, "message": "User not found in pending list"}


@app.post("/api/admin/deny")
async def deny_user(request: Request):
    """Deny a pending access request (admin only)."""
    if not auth.is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    data = await request.json()
    email = data.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    success = user_store.deny(email)

    if success:
        print(f"Admin denied access for: {email}")
        return {"success": True, "message": f"Denied {email}"}
    else:
        return {"success": False, "message": "User not found in pending list"}


# HTML Routes

@app.get("/login.html", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    html_path = Path(__file__).parent.parent / "frontend" / "login.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Login page not found</h1>")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the dashboard HTML."""
    # Check authentication
    if not auth.is_authenticated(request):
        return RedirectResponse("/login.html")

    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Dashboard not found. Please check frontend/index.html</h1>")


@app.get("/settings.html", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page (admin only)."""
    # Check authentication
    if not auth.is_authenticated(request):
        return RedirectResponse("/login.html")

    # Check if user is admin
    if not auth.is_admin_user(request):
        return RedirectResponse("/")  # Non-admins redirect to dashboard

    html_path = Path(__file__).parent.parent / "frontend" / "settings.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Settings page not found</h1>")


@app.get("/pending.html", response_class=HTMLResponse)
async def pending_page():
    """Serve the pending access page."""
    html_path = Path(__file__).parent.parent / "frontend" / "pending.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Pending page not found</h1>")


@app.get("/demo.html", response_class=HTMLResponse)
async def demo_page(request: Request):
    """Serve the UI redesign demo page."""
    # Check authentication
    if not auth.is_authenticated(request):
        return RedirectResponse("/login.html")

    html_path = Path(__file__).parent.parent / "frontend" / "demo.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Demo page not found</h1>")


@app.get("/api/status", response_model=StatusResponse)
async def get_status(user: dict = Depends(auth.get_current_user)):
    """Get current printer status and telemetry."""
    global printer_client, current_gcode_metadata, print_start_time

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    state = printer_client.get_state()

    # Calculate time remaining
    time_remaining_seconds = 0
    time_remaining_formatted = "00:00:00"

    if current_gcode_metadata and state.status == PrinterStatus.PRINTING:
        total_time = current_gcode_metadata.estimated_time_seconds
        if print_start_time and total_time > 0:
            elapsed = (datetime.now() - print_start_time).total_seconds()
            time_remaining_seconds = max(0, int(total_time - elapsed))

            # Also consider progress percentage as a fallback
            if state.progress > 0:
                progress_based_remaining = int(total_time * (100 - state.progress) / 100)
                # Use average of both methods
                time_remaining_seconds = int((time_remaining_seconds + progress_based_remaining) / 2)

            hours = time_remaining_seconds // 3600
            minutes = (time_remaining_seconds % 3600) // 60
            seconds = time_remaining_seconds % 60
            time_remaining_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return StatusResponse(
        connected=state.connected,
        status=state.status.value,
        nozzle_temp=state.nozzle_temp,
        nozzle_target=state.nozzle_target,
        bed_temp=state.bed_temp,
        bed_target=state.bed_target,
        progress=state.progress,
        led_on=state.led_on,
        time_remaining_seconds=time_remaining_seconds,
        time_remaining_formatted=time_remaining_formatted,
        gcode_filename=current_gcode_metadata.filename if current_gcode_metadata else None,
    )


@app.post("/api/control")
async def control_printer(cmd: ControlCommand, user: dict = Depends(auth.get_current_user)):
    """Send control command to printer."""
    global printer_client

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    if not printer_client.state.connected:
        raise HTTPException(status_code=503, detail="Printer not connected")

    success = False
    message = ""

    if cmd.command == "emergency_stop":
        success = printer_client.emergency_stop()
        message = "Emergency stop sent" if success else "Failed to send emergency stop"
    elif cmd.command == "led_on":
        success = printer_client.toggle_led(on=True)
        message = "LED turned on" if success else "Failed to turn on LED"
    elif cmd.command == "led_off":
        success = printer_client.toggle_led(on=False)
        message = "LED turned off" if success else "Failed to turn off LED"
    elif cmd.command == "pause":
        success = printer_client.pause_print()
        message = "Print paused" if success else "Failed to pause print"
    elif cmd.command == "resume":
        success = printer_client.resume_print()
        message = "Print resumed" if success else "Failed to resume print"
    elif cmd.command == "fan_on":
        success = printer_client.fan_on()
        message = "Fan turned on" if success else "Failed to turn on fan"
    elif cmd.command == "fan_off":
        success = printer_client.fan_off()
        message = "Fan turned off" if success else "Failed to turn off fan"
    elif cmd.command == "disable_motors":
        success = printer_client.disable_motors()
        message = "Motors disabled" if success else "Failed to disable motors"
    elif cmd.command == "home_axes":
        success = printer_client.home_axes()
        message = "Homing all axes" if success else "Failed to home axes"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {cmd.command}")

    return {"success": success, "message": message}


@app.get("/api/position")
async def get_position(user: dict = Depends(auth.get_current_user)):
    """Get current printer position."""
    global printer_client

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    if not printer_client.state.connected:
        return {"x": 0, "y": 0, "z": 0}

    position = printer_client.get_position()
    return position


class TemperatureCommand(BaseModel):
    target: str  # "nozzle" or "bed"
    temperature: int


@app.post("/api/temperature")
async def set_temperature(cmd: TemperatureCommand, user: dict = Depends(auth.get_current_user)):
    """Set nozzle or bed temperature."""
    global printer_client

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    if not printer_client.state.connected:
        raise HTTPException(status_code=503, detail="Printer not connected")

    success = False
    message = ""

    if cmd.target == "nozzle":
        success = printer_client.set_nozzle_temp(cmd.temperature)
        message = f"Nozzle target set to {cmd.temperature}°C" if success else "Failed to set nozzle temperature"
    elif cmd.target == "bed":
        success = printer_client.set_bed_temp(cmd.temperature)
        message = f"Bed target set to {cmd.temperature}°C" if success else "Failed to set bed temperature"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown target: {cmd.target}")

    return {"success": success, "message": message}


class UploadOptions(BaseModel):
    upload_to_printer: bool = False
    start_print: bool = False


@app.post("/api/gcode/upload")
async def upload_gcode(
    file: UploadFile = File(...),
    upload_to_printer: bool = False,
    start_print: bool = False,
    user: dict = Depends(auth.get_current_user)
):
    """Upload and parse a G-code file. Optionally upload to printer and/or start printing."""
    global current_gcode_metadata, print_start_time, printer_client

    if not file.filename.lower().endswith(('.gcode', '.gco', '.g')):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a G-code file.")

    # Read file content
    content = await file.read()

    # File size validation (100MB max from config)
    max_size = config.get("gcode", {}).get("max_file_size_mb", 100) * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        )

    # Basic content validation - check if it's text-like
    try:
        content_str = content.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid file content. G-code files must be text files."
        )

    # Check if file contains G-code commands
    if not any(line.strip().startswith(('G', 'M', ';')) for line in content_str.split('\n')[:50]):
        raise HTTPException(
            status_code=400,
            detail="File doesn't appear to contain valid G-code commands."
        )

    # Parse G-code for metadata
    parser = GCodeParser()
    current_gcode_metadata = parser.parse_content(content_str, file.filename)
    print_start_time = datetime.now()

    result = {
        "success": True,
        "filename": current_gcode_metadata.filename,
        "estimated_time_seconds": current_gcode_metadata.estimated_time_seconds,
        "estimated_time_formatted": current_gcode_metadata.estimated_time_formatted,
        "filament_used_mm": current_gcode_metadata.filament_used_mm,
        "total_layers": current_gcode_metadata.total_layers,
        "uploaded_to_printer": False,
        "print_started": False
    }

    # Upload to printer if requested
    if upload_to_printer and printer_client and printer_client.state.connected:
        if printer_client.upload_file(file.filename, content):
            result["uploaded_to_printer"] = True

            # Start printing if requested
            if start_print:
                if printer_client.start_print(file.filename):
                    result["print_started"] = True
                else:
                    result["message"] = "Uploaded but failed to start print"
        else:
            result["success"] = False
            result["message"] = "Failed to upload to printer"

    return result


@app.get("/api/files")
async def list_files(user: dict = Depends(auth.get_current_user)):
    """List files on the printer's SD card."""
    global printer_client

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    if not printer_client.state.connected:
        raise HTTPException(status_code=503, detail="Printer not connected")

    files = printer_client.list_files()
    return {"success": True, "files": files}


class PrintFileCommand(BaseModel):
    filename: str


@app.post("/api/files/print")
async def start_print_file(cmd: PrintFileCommand, user: dict = Depends(auth.get_current_user)):
    """Start printing a file from the printer's SD card."""
    global printer_client, print_start_time

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    if not printer_client.state.connected:
        raise HTTPException(status_code=503, detail="Printer not connected")

    success = printer_client.start_print(cmd.filename)
    if success:
        print_start_time = datetime.now()

    return {
        "success": success,
        "message": f"Started printing {cmd.filename}" if success else f"Failed to start print"
    }


class DeleteFileCommand(BaseModel):
    filename: str


@app.post("/api/files/delete")
async def delete_file(cmd: DeleteFileCommand, user: dict = Depends(auth.get_current_user)):
    """Delete a file from the printer's SD card."""
    global printer_client

    if not printer_client:
        raise HTTPException(status_code=503, detail="Printer client not initialized")

    if not printer_client.state.connected:
        raise HTTPException(status_code=503, detail="Printer not connected")

    success = printer_client.delete_file(cmd.filename)

    return {
        "success": success,
        "message": f"Deleted {cmd.filename}" if success else f"Failed to delete file"
    }


@app.post("/api/notifications/test")
async def test_notification(user: dict = Depends(auth.get_current_user)):
    """Send a test notification to the configured webhook."""
    await send_notification("test", "Test notification from FlashForge Monitor")
    return {"success": True, "message": "Test notification sent"}


@app.get("/api/config")
async def get_config(user: dict = Depends(auth.get_current_user)):
    """Get current configuration (sensitive data masked)."""
    return {
        "version": VERSION,
        "printer_ip": config["printer"]["ip_address"],
        "poll_interval": config["printer"]["poll_interval"],
        "n8n_webhook_configured": bool(config.get("notifications", {}).get("n8n_webhook_url")),
    }


@app.get("/api/config/full")
async def get_full_config(user: dict = Depends(auth.get_current_user)):
    """Get full configuration for settings page."""
    return {
        "version": VERSION,
        "printer": config.get("printer", {}),
        "material_presets": config.get("material_presets", {
            "pla": {"nozzle": 200, "bed": 60},
            "petg": {"nozzle": 235, "bed": 80},
            "abs": {"nozzle": 230, "bed": 100},
            "asa": {"nozzle": 240, "bed": 100}
        }),
        "notifications": config.get("notifications", {}),
        "gcode": config.get("gcode", {}),
        "server": {
            "host": config.get("server", {}).get("host", "127.0.0.1"),
            "port": config.get("server", {}).get("port", 8000)
        }
    }


@app.post("/api/config")
async def update_config(update: ConfigUpdate, user: dict = Depends(auth.get_current_user)):
    """Update configuration dynamically."""
    global printer_client, config

    # Validate printer IP if provided
    if update.printer_ip:
        if not validate_ip_address(update.printer_ip):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid IP address format: {update.printer_ip}"
            )
        config["printer"]["ip_address"] = update.printer_ip
        # Reconnect with new IP
        if printer_client:
            printer_client.disconnect()
            printer_client = PrinterClient(update.printer_ip)
            printer_client.connect()
            printer_client.add_status_callback(status_change_callback)
            printer_client.start_polling()

    # Validate webhook URL if provided
    if update.n8n_webhook_url is not None:
        if not validate_webhook_url(update.n8n_webhook_url):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid webhook URL format. Must be http:// or https://"
            )
        if "notifications" not in config:
            config["notifications"] = {}
        config["notifications"]["n8n_webhook_url"] = update.n8n_webhook_url

    # Save config to file
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return {"success": True, "message": "Configuration updated"}


class FullConfigUpdate(BaseModel):
    printer: Optional[dict] = None
    material_presets: Optional[dict] = None
    notifications: Optional[dict] = None
    gcode: Optional[dict] = None


@app.post("/api/config/full")
async def update_full_config(update: FullConfigUpdate, user: dict = Depends(auth.get_current_user)):
    """Update full configuration from settings page."""
    global printer_client, config

    # Update printer settings
    if update.printer:
        if "ip_address" in update.printer:
            if not validate_ip_address(update.printer["ip_address"]):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid IP address format: {update.printer['ip_address']}"
                )
        config["printer"].update(update.printer)

        # Reconnect if IP changed
        if "ip_address" in update.printer and printer_client:
            printer_client.disconnect()
            printer_client = PrinterClient(update.printer["ip_address"])
            import threading
            def reconnect():
                try:
                    if printer_client.connect():
                        printer_client.add_status_callback(status_change_callback)
                        printer_client.start_polling()
                except Exception as e:
                    print(f"Reconnection error: {e}")
            threading.Thread(target=reconnect, daemon=True).start()

    # Update material presets
    if update.material_presets:
        config["material_presets"] = update.material_presets

    # Update notifications
    if update.notifications:
        if "n8n_webhook_url" in update.notifications:
            if not validate_webhook_url(update.notifications["n8n_webhook_url"]):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid webhook URL format. Must be http:// or https://"
                )
        config["notifications"].update(update.notifications)

    # Update G-code settings
    if update.gcode:
        if "gcode" not in config:
            config["gcode"] = {}
        config["gcode"].update(update.gcode)

    # Save config to file
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return {"success": True, "message": "Configuration updated and saved"}


@app.post("/api/scan-network")
async def scan_network(user: dict = Depends(auth.get_current_user)):
    """Scan local network for FlashForge printers."""
    import socket
    import concurrent.futures
    from ipaddress import IPv4Network

    # Get current printer IP to determine subnet
    current_ip = config["printer"]["ip_address"]

    # Determine subnet (assumes /24)
    try:
        ip_parts = current_ip.split('.')
        subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
    except:
        subnet = "192.168.1.0/24"  # Default fallback

    found_printers = []

    def check_printer(ip: str) -> Optional[str]:
        """Check if a printer is at this IP by testing port 8899."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # Fast timeout for network scan
            result = sock.connect_ex((ip, 8899))
            sock.close()

            if result == 0:
                # Port is open, try handshake to verify it's a FlashForge printer
                try:
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(1.0)
                    test_sock.connect((ip, 8899))
                    test_sock.sendall(b"~M601 S1\r\n")
                    response = test_sock.recv(1024)
                    test_sock.close()

                    if b"ok" in response.lower():
                        return ip
                except:
                    pass
        except:
            pass
        return None

    # Scan network in parallel
    network = IPv4Network(subnet, strict=False)
    ips_to_scan = [str(ip) for ip in list(network.hosts())[:254]]  # Limit to first 254

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_printer, ips_to_scan)
        found_printers = [ip for ip in results if ip is not None]

    return {
        "success": True,
        "printers": found_printers,
        "scanned_subnet": subnet
    }


@app.get("/api/camera")
async def get_camera_url(user: dict = Depends(auth.get_current_user)):
    """Get the camera stream URL."""
    printer_ip = config["printer"]["ip_address"]
    camera_port = config["printer"].get("camera_port", 8080)
    return {
        "stream_url": f"/api/camera/stream",  # Use proxy path
        "snapshot_url": f"http://{printer_ip}:{camera_port}/?action=snapshot",
    }


@app.get("/api/camera/stream")
def camera_stream_proxy(user: dict = Depends(auth.get_current_user)):
    """Proxy the MJPEG camera stream from the printer."""
    printer_ip = config["printer"]["ip_address"]
    camera_port = config["printer"].get("camera_port", 8080)
    camera_url = f"http://{printer_ip}:{camera_port}/?action=stream"

    def generate():
        """Stream camera data directly from printer."""
        r = requests.get(camera_url, stream=True, timeout=(5, None))
        # Stream chunks continuously - let the connection stay open
        for chunk in r.iter_content(chunk_size=8192):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type='multipart/x-mixed-replace; boundary=boundarydonotcross',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )


@app.post("/api/reconnect")
async def reconnect_printer(user: dict = Depends(auth.get_current_user)):
    """Force reconnection to the printer."""
    global printer_client

    if printer_client:
        printer_client.disconnect()
        success = printer_client.connect()
        if success:
            printer_client.start_polling()
        return {"success": success, "message": "Reconnected" if success else "Failed to reconnect"}

    return {"success": False, "message": "Printer client not initialized"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config["server"]["host"],
        port=config["server"]["port"],
        reload=config["server"].get("debug", False)
    )
