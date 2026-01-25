"""
FlashForge Adventurer 3 Monitor - FastAPI Backend

Provides REST API for printer status, control, and notifications.
"""

import os
import asyncio
import httpx
import requests
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

from .printer_client import PrinterClient, PrinterState, PrinterStatus
from .gcode_parser import GCodeParser, GCodeMetadata

VERSION = "1.2.2"

# Load configuration
def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {
        "printer": {"ip_address": "192.168.1.100", "poll_interval": 5},
        "server": {"host": "0.0.0.0", "port": 8000},
        "notifications": {"n8n_webhook_url": "", "notify_on_complete": True},
    }


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


# API Routes

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard HTML."""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Dashboard not found. Please check frontend/index.html</h1>")


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
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
async def control_printer(cmd: ControlCommand):
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
    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {cmd.command}")

    return {"success": success, "message": message}


class TemperatureCommand(BaseModel):
    target: str  # "nozzle" or "bed"
    temperature: int


@app.post("/api/temperature")
async def set_temperature(cmd: TemperatureCommand):
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
    start_print: bool = False
):
    """Upload and parse a G-code file. Optionally upload to printer and/or start printing."""
    global current_gcode_metadata, print_start_time, printer_client

    if not file.filename.lower().endswith(('.gcode', '.gco', '.g')):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be a G-code file.")

    # Read file content
    content = await file.read()
    content_str = content.decode('utf-8', errors='ignore')

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
async def list_files():
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
async def start_print_file(cmd: PrintFileCommand):
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
async def delete_file(cmd: DeleteFileCommand):
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
async def test_notification():
    """Send a test notification to the configured webhook."""
    await send_notification("test", "Test notification from FlashForge Monitor")
    return {"success": True, "message": "Test notification sent"}


@app.get("/api/config")
async def get_config():
    """Get current configuration (sensitive data masked)."""
    return {
        "version": VERSION,
        "printer_ip": config["printer"]["ip_address"],
        "poll_interval": config["printer"]["poll_interval"],
        "n8n_webhook_configured": bool(config.get("notifications", {}).get("n8n_webhook_url")),
    }


@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """Update configuration dynamically."""
    global printer_client, config

    if update.printer_ip:
        config["printer"]["ip_address"] = update.printer_ip
        # Reconnect with new IP
        if printer_client:
            printer_client.disconnect()
            printer_client = PrinterClient(update.printer_ip)
            printer_client.connect()
            printer_client.add_status_callback(status_change_callback)
            printer_client.start_polling()

    if update.n8n_webhook_url is not None:
        if "notifications" not in config:
            config["notifications"] = {}
        config["notifications"]["n8n_webhook_url"] = update.n8n_webhook_url

    # Save config to file
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return {"success": True, "message": "Configuration updated"}


@app.get("/api/camera")
async def get_camera_url():
    """Get the camera stream URL."""
    printer_ip = config["printer"]["ip_address"]
    camera_port = config["printer"].get("camera_port", 8080)
    return {
        "stream_url": f"/api/camera/stream",  # Use proxy path
        "snapshot_url": f"http://{printer_ip}:{camera_port}/?action=snapshot",
    }


@app.get("/api/camera/stream")
def camera_stream_proxy():
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
async def reconnect_printer():
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
