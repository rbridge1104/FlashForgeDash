"""
FlashForge Adventurer 3 Printer Client

Handles TCP communication with the printer over port 8899.
Implements the FlashForge protocol for telemetry and control.
"""

import socket
import logging
import threading
import time
from typing import Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrinterStatus(Enum):
    IDLE = "idle"
    PREHEATING = "preheating"
    HEATING = "heating"
    COOLING = "cooling"
    READY = "ready"
    PRINTING = "printing"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class PrinterState:
    """Current state of the printer."""
    connected: bool = False
    status: PrinterStatus = PrinterStatus.DISCONNECTED
    nozzle_temp: float = 0.0
    nozzle_target: float = 0.0
    bed_temp: float = 0.0
    bed_target: float = 0.0
    progress: int = 0
    led_on: bool = True
    error_message: str = ""
    last_update: float = field(default_factory=time.time)


class PrinterClient:
    """TCP client for FlashForge Adventurer 3 printer communication."""

    CONTROL_PORT = 8899
    RECV_TIMEOUT = 5.0
    POLL_INTERVAL = 5.0

    def __init__(self, ip_address: str):
        self.ip_address = ip_address
        self.socket: Optional[socket.socket] = None
        self.state = PrinterState()
        self._lock = threading.Lock()
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._status_callbacks: list[Callable[[PrinterState], None]] = []

    def _send_command(self, command: str) -> Optional[str]:
        """Send a command to the printer and return the response."""
        if not self.socket:
            return None

        try:
            # FlashForge protocol requires commands to end with \r\n
            full_command = f"{command}\r\n"
            self.socket.sendall(full_command.encode('utf-8'))

            # Read response
            response = b""
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    # Check for end of response (ok\r\n)
                    if b"ok\r\n" in response or b"Error" in response:
                        break
                except socket.timeout:
                    break

            return response.decode('utf-8', errors='ignore')
        except (socket.error, OSError) as e:
            logger.error(f"Error sending command: {e}")
            return None

    def connect(self) -> bool:
        """Establish connection to the printer with M601 S1 handshake."""
        with self._lock:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.RECV_TIMEOUT)
                self.socket.connect((self.ip_address, self.CONTROL_PORT))

                # Send handshake command
                response = self._send_command("~M601 S1")
                if response and "ok" in response.lower():
                    self.state.connected = True
                    self.state.status = PrinterStatus.IDLE
                    logger.info(f"Connected to printer at {self.ip_address}")
                    return True
                else:
                    logger.error(f"Handshake failed: {response}")
                    self._close_socket()
                    return False

            except (socket.error, OSError) as e:
                logger.error(f"Connection failed: {e}")
                self._close_socket()
                return False

    def disconnect(self) -> None:
        """Close the connection to the printer."""
        self._running = False
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)
        self._close_socket()

    def _close_socket(self) -> None:
        """Close the socket connection."""
        with self._lock:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            self.state.connected = False
            self.state.status = PrinterStatus.DISCONNECTED

    def _parse_temperatures(self, response: str) -> None:
        """Parse M105 temperature response."""
        # Expected format: T0:200/200 B:60/60
        try:
            if "T0:" in response:
                # Extract nozzle temperature
                t0_part = response.split("T0:")[1].split()[0]
                if "/" in t0_part:
                    current, target = t0_part.split("/")
                    self.state.nozzle_temp = float(current)
                    self.state.nozzle_target = float(target)

            if "B:" in response:
                # Extract bed temperature
                b_part = response.split("B:")[1].split()[0]
                if "/" in b_part:
                    current, target = b_part.split("/")
                    self.state.bed_temp = float(current)
                    self.state.bed_target = float(target)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse temperatures: {e}")

    def _parse_status(self, response: str) -> None:
        """Parse M119 status response and determine intelligent status."""
        response_lower = response.lower()

        # First, check explicit printer states
        if "printing" in response_lower:
            self.state.status = PrinterStatus.PRINTING
        elif "paused" in response_lower:
            self.state.status = PrinterStatus.PAUSED
        elif "complete" in response_lower or "finished" in response_lower:
            self.state.status = PrinterStatus.COMPLETE
        elif "error" in response_lower:
            self.state.status = PrinterStatus.ERROR
        elif self.state.connected:
            # Determine status based on temperature state
            self.state.status = self._determine_thermal_status()

    def _parse_progress(self, response: str) -> None:
        """Parse M27 progress response for SD card printing status."""
        # M27 response formats:
        # "SD printing byte X/Y" - actively printing
        # "Not SD printing" - not printing from SD
        if "SD printing byte" in response or "SD printing" in response:
            try:
                # Format: SD printing byte X/Y
                if "byte" in response:
                    parts = response.split("byte")[1].strip().split("/")
                    if len(parts) == 2:
                        current = int(parts[0].strip())
                        total = int(parts[1].split()[0].strip())  # Handle trailing "ok"
                        if total > 0:
                            self.state.progress = int((current / total) * 100)
                            logger.debug(f"SD print progress: {self.state.progress}% ({current}/{total} bytes)")
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse M27 progress: {e}")
        elif "not" in response.lower() and "printing" in response.lower():
            # Not printing from SD - reset progress if we're not in a print state
            if self.state.status not in [PrinterStatus.PRINTING, PrinterStatus.PAUSED]:
                self.state.progress = 0

    def _determine_thermal_status(self) -> PrinterStatus:
        """Determine printer status based on thermal state."""
        # If there's active progress, printer is likely printing (M119 might not report it)
        if self.state.progress > 0 and self.state.progress < 100:
            return PrinterStatus.PRINTING

        # Temperature tolerance (degrees C)
        TEMP_TOLERANCE = 3.0
        HEATING_THRESHOLD = 10.0  # Consider "heating" if more than 10° below target

        nozzle_diff = self.state.nozzle_target - self.state.nozzle_temp
        bed_diff = self.state.bed_target - self.state.bed_temp

        # Check if targets are set
        nozzle_target_set = self.state.nozzle_target > 30  # Above room temp
        bed_target_set = self.state.bed_target > 30

        # Check if heating
        nozzle_heating = nozzle_target_set and nozzle_diff > TEMP_TOLERANCE
        bed_heating = bed_target_set and bed_diff > TEMP_TOLERANCE

        # Check if significantly below target (preheating)
        nozzle_preheating = nozzle_target_set and nozzle_diff > HEATING_THRESHOLD
        bed_preheating = bed_target_set and bed_diff > HEATING_THRESHOLD

        # Check if cooling (temp above target)
        nozzle_cooling = self.state.nozzle_temp > (self.state.nozzle_target + TEMP_TOLERANCE) and self.state.nozzle_temp > 40
        bed_cooling = self.state.bed_temp > (self.state.bed_target + TEMP_TOLERANCE) and self.state.bed_temp > 40

        # Check if at target temperature
        nozzle_ready = nozzle_target_set and abs(nozzle_diff) <= TEMP_TOLERANCE
        bed_ready = bed_target_set and abs(bed_diff) <= TEMP_TOLERANCE

        # Determine status priority:
        # 1. PREHEATING - Both nozzle and bed significantly below target
        if nozzle_preheating and bed_preheating:
            return PrinterStatus.PREHEATING

        # 2. HEATING - Either component heating (but not both preheating)
        if nozzle_heating or bed_heating:
            return PrinterStatus.HEATING

        # 3. READY - At target temperature(s)
        if (nozzle_ready or not nozzle_target_set) and (bed_ready or not bed_target_set):
            if nozzle_target_set or bed_target_set:
                return PrinterStatus.READY

        # 4. COOLING - Actively cooling down
        if nozzle_cooling or bed_cooling:
            return PrinterStatus.COOLING

        # 5. IDLE - No active thermal management
        return PrinterStatus.IDLE

    def poll_status(self) -> PrinterState:
        """Poll printer for current status and temperatures."""
        with self._lock:
            if not self.state.connected:
                return self.state

            # Get temperatures (M105)
            temp_response = self._send_command("~M105")
            if temp_response:
                self._parse_temperatures(temp_response)
            else:
                self._handle_connection_error()
                return self.state

            # Get status (M119)
            status_response = self._send_command("~M119")
            if status_response:
                self._parse_status(status_response)
            else:
                self._handle_connection_error()
                return self.state

            # Get SD card print progress (M27) - critical for manual prints
            progress_response = self._send_command("~M27")
            if progress_response:
                self._parse_progress(progress_response)

            self.state.last_update = time.time()
            return self.state

    def _handle_connection_error(self) -> None:
        """Handle connection errors with automatic reconnection."""
        logger.warning("Connection error detected, attempting reconnect...")
        self._close_socket()
        time.sleep(1)
        self.connect()

    def start_polling(self) -> None:
        """Start background polling thread."""
        if self._running:
            return

        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                state = self.poll_status()
                for callback in self._status_callbacks:
                    try:
                        callback(state)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            except Exception as e:
                logger.error(f"Polling error: {e}")

            time.sleep(self.POLL_INTERVAL)

    def add_status_callback(self, callback: Callable[[PrinterState], None]) -> None:
        """Add a callback to be called when status changes."""
        self._status_callbacks.append(callback)

    # Control commands

    def emergency_stop(self) -> bool:
        """Send emergency stop command (M112)."""
        with self._lock:
            response = self._send_command("~M112")
            return response is not None and "ok" in response.lower()

    def toggle_led(self, on: bool = True) -> bool:
        """Toggle LED light (M146)."""
        with self._lock:
            # M146 r<val> g<val> b<val> F<freq>
            # For on: full white, for off: all zeros
            if on:
                response = self._send_command("~M146 r255 g255 b255 F0")
            else:
                response = self._send_command("~M146 r0 g0 b0 F0")

            if response and "ok" in response.lower():
                self.state.led_on = on
                return True
            return False

    def pause_print(self) -> bool:
        """Pause the current print job."""
        with self._lock:
            response = self._send_command("~M25")
            return response is not None and "ok" in response.lower()

    def resume_print(self) -> bool:
        """Resume a paused print job."""
        with self._lock:
            response = self._send_command("~M24")
            return response is not None and "ok" in response.lower()

    def set_nozzle_temp(self, temperature: int) -> bool:
        """Set nozzle temperature (M104)."""
        with self._lock:
            temp = max(0, min(300, temperature))  # Clamp 0-300
            response = self._send_command(f"~M104 S{temp}")
            if response and "ok" in response.lower():
                self.state.nozzle_target = float(temp)
                return True
            return False

    def set_bed_temp(self, temperature: int) -> bool:
        """Set bed temperature (M140)."""
        with self._lock:
            temp = max(0, min(120, temperature))  # Clamp 0-120
            response = self._send_command(f"~M140 S{temp}")
            if response and "ok" in response.lower():
                self.state.bed_target = float(temp)
                return True
            return False

    def get_state(self) -> PrinterState:
        """Get the current printer state."""
        return self.state

    # Additional control commands

    def fan_on(self) -> bool:
        """Turn on cooling fan (M106)."""
        with self._lock:
            response = self._send_command("~M106")
            return response is not None and "ok" in response.lower()

    def fan_off(self) -> bool:
        """Turn off cooling fan (M107)."""
        with self._lock:
            response = self._send_command("~M107")
            return response is not None and "ok" in response.lower()

    def disable_motors(self) -> bool:
        """Disable stepper motors (M18) - allows manual movement."""
        with self._lock:
            response = self._send_command("~M18")
            return response is not None and "ok" in response.lower()

    def home_axes(self) -> bool:
        """Home all axes (G28)."""
        with self._lock:
            response = self._send_command("~G28")
            return response is not None and "ok" in response.lower()

    def get_position(self) -> dict:
        """Get current position (M114)."""
        with self._lock:
            response = self._send_command("~M114")
            if not response:
                return {"x": 0, "y": 0, "z": 0}

            # Parse response like: X:125.0 Y:125.0 Z:0.0
            position = {"x": 0, "y": 0, "z": 0}
            try:
                if "X:" in response:
                    x_part = response.split("X:")[1].split()[0]
                    position["x"] = float(x_part)
                if "Y:" in response:
                    y_part = response.split("Y:")[1].split()[0]
                    position["y"] = float(y_part)
                if "Z:" in response:
                    z_part = response.split("Z:")[1].split()[0]
                    position["z"] = float(z_part)
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse position: {e}")

            return position

    # File management commands

    def list_files(self) -> list[dict]:
        """List files on the printer's internal storage.

        Note: FlashForge Adventurer 3 uses internal storage, not SD card.
        The M20 command may not work for internal storage.
        This is a limitation of the FlashForge protocol.
        """
        with self._lock:
            # Try M20 for internal storage
            response = self._send_command("~M20")
            if not response:
                logger.warning("No response from M20 command")
                return []

            logger.info(f"M20 response: {repr(response)}")

            files = []
            lines = response.split('\n')

            for line in lines:
                line = line.strip()
                # Skip command echo, received, and ok lines
                if not line or line.startswith('ok') or line.startswith('CMD') or line.startswith('Received'):
                    continue

                # Look for any line that might be a filename
                logger.info(f"Processing line: {repr(line)}")

                # If line contains common file extensions
                if any(ext in line.lower() for ext in ['.gcode', '.gco', '.g ']):
                    parts = line.split()
                    if parts:
                        filename = parts[0]
                        size = 0
                        # Try to extract size if available
                        for i, part in enumerate(parts):
                            if part.isdigit() and i + 1 < len(parts) and 'byte' in parts[i + 1].lower():
                                size = int(part)
                                break
                        files.append({'filename': filename, 'size': size})
                        logger.info(f"Found file: {filename} ({size} bytes)")

            if not files:
                logger.info("No files found. Note: FlashForge Adventurer 3 uses internal storage. File listing via M20 may not be supported.")

            return files

    def start_print(self, filename: str) -> bool:
        """Start printing a file from the SD card."""
        with self._lock:
            # First select the file (M23)
            select_response = self._send_command(f"~M23 {filename}")
            if not select_response or "ok" not in select_response.lower():
                logger.error(f"Failed to select file: {filename}")
                return False

            # Then start printing (M24)
            start_response = self._send_command("~M24")
            if start_response and "ok" in start_response.lower():
                logger.info(f"Started printing: {filename}")
                return True
            return False

    def delete_file(self, filename: str) -> bool:
        """Delete a file from the SD card (M30)."""
        with self._lock:
            response = self._send_command(f"~M30 {filename}")
            if response and "ok" in response.lower():
                logger.info(f"Deleted file: {filename}")
                return True
            logger.error(f"Failed to delete file: {filename}")
            return False

    def upload_file(self, filename: str, content: bytes) -> bool:
        """Upload a file to the printer's SD card."""
        with self._lock:
            # M28 begins writing to SD card
            begin_response = self._send_command(f"~M28 {filename}")
            if not begin_response or "ok" not in begin_response.lower():
                logger.error("Failed to begin file upload")
                return False

            # Send file content line by line
            try:
                lines = content.decode('utf-8', errors='ignore').split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(';'):  # Skip comments
                        self._send_command(line)

                # M29 stops writing to SD card
                end_response = self._send_command("~M29")
                if end_response and "ok" in end_response.lower():
                    logger.info(f"Successfully uploaded: {filename}")
                    return True
            except Exception as e:
                logger.error(f"Upload failed: {e}")
            return False
