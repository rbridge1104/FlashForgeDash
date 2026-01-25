"""
G-code Parser for Orca Slicer

Extracts estimated printing time and other metadata from G-code files.
"""

import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class GCodeMetadata:
    """Metadata extracted from G-code file."""
    estimated_time_seconds: int = 0
    estimated_time_formatted: str = "00:00:00"
    filament_used_mm: float = 0.0
    filament_used_grams: float = 0.0
    layer_height: float = 0.0
    total_layers: int = 0
    nozzle_temp: float = 0.0
    bed_temp: float = 0.0
    filename: str = ""


class GCodeParser:
    """Parser for Orca Slicer G-code files."""

    # Patterns for extracting metadata from comments
    PATTERNS = {
        # Orca Slicer / PrusaSlicer style
        "estimated_time": [
            r";\s*estimated printing time.*?=\s*(.+)",
            r";\s*TIME:\s*(\d+)",
            r";\s*PRINT_TIME:\s*(\d+)",
            r";\s*total estimated time:\s*(.+)",
        ],
        "filament_mm": [
            r";\s*filament used \[mm\]\s*=\s*([\d.]+)",
            r";\s*FILAMENT_USED:\s*([\d.]+)",
        ],
        "filament_grams": [
            r";\s*filament used \[g\]\s*=\s*([\d.]+)",
            r";\s*total filament used \[g\]\s*=\s*([\d.]+)",
        ],
        "layer_height": [
            r";\s*layer_height\s*=\s*([\d.]+)",
            r";\s*LAYER_HEIGHT:\s*([\d.]+)",
        ],
        "total_layers": [
            r";\s*total layers count\s*=\s*(\d+)",
            r";\s*LAYER_COUNT:\s*(\d+)",
        ],
        "nozzle_temp": [
            r";\s*nozzle_temperature\s*=\s*(\d+)",
            r";\s*temperature\s*=\s*(\d+)",
        ],
        "bed_temp": [
            r";\s*bed_temperature\s*=\s*(\d+)",
            r";\s*first_layer_bed_temperature\s*=\s*(\d+)",
        ],
    }

    def __init__(self):
        self.metadata = GCodeMetadata()

    def _parse_time_string(self, time_str: str) -> int:
        """Convert time string to seconds."""
        time_str = time_str.strip().lower()

        # Try pure seconds first
        if time_str.isdigit():
            return int(time_str)

        total_seconds = 0

        # Parse formats like "1h 30m 45s" or "1d 2h 30m"
        patterns = [
            (r"(\d+)\s*d", 86400),  # days
            (r"(\d+)\s*h", 3600),   # hours
            (r"(\d+)\s*m(?:in)?", 60),  # minutes
            (r"(\d+)\s*s(?:ec)?", 1),   # seconds
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, time_str)
            if match:
                total_seconds += int(match.group(1)) * multiplier

        # Try HH:MM:SS format
        if total_seconds == 0:
            match = re.match(r"(\d+):(\d+):(\d+)", time_str)
            if match:
                h, m, s = map(int, match.groups())
                total_seconds = h * 3600 + m * 60 + s

        return total_seconds

    def _format_time(self, seconds: int) -> str:
        """Format seconds as HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _extract_match(self, content: str, patterns: list) -> Optional[str]:
        """Try multiple patterns and return the first match."""
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def parse_file(self, filepath: str) -> GCodeMetadata:
        """Parse a G-code file and extract metadata."""
        self.metadata = GCodeMetadata()
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"G-code file not found: {filepath}")

        self.metadata.filename = path.name

        # Read only the first portion of the file (metadata is usually at the top)
        # and the last portion (some slicers put summaries at the end)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first 500 lines
            head_lines = []
            for i, line in enumerate(f):
                if i >= 500:
                    break
                head_lines.append(line)

            # Seek to approximate end and read last portion
            f.seek(0, 2)  # End of file
            file_size = f.tell()
            read_size = min(50000, file_size)  # Last 50KB
            f.seek(max(0, file_size - read_size))
            tail_content = f.read()

        content = ''.join(head_lines) + '\n' + tail_content

        # Extract estimated time
        time_str = self._extract_match(content, self.PATTERNS["estimated_time"])
        if time_str:
            self.metadata.estimated_time_seconds = self._parse_time_string(time_str)
            self.metadata.estimated_time_formatted = self._format_time(
                self.metadata.estimated_time_seconds
            )

        # Extract filament usage
        filament_mm = self._extract_match(content, self.PATTERNS["filament_mm"])
        if filament_mm:
            self.metadata.filament_used_mm = float(filament_mm)

        filament_g = self._extract_match(content, self.PATTERNS["filament_grams"])
        if filament_g:
            self.metadata.filament_used_grams = float(filament_g)

        # Extract layer info
        layer_height = self._extract_match(content, self.PATTERNS["layer_height"])
        if layer_height:
            self.metadata.layer_height = float(layer_height)

        total_layers = self._extract_match(content, self.PATTERNS["total_layers"])
        if total_layers:
            self.metadata.total_layers = int(total_layers)

        # Extract temperature settings
        nozzle_temp = self._extract_match(content, self.PATTERNS["nozzle_temp"])
        if nozzle_temp:
            self.metadata.nozzle_temp = float(nozzle_temp)

        bed_temp = self._extract_match(content, self.PATTERNS["bed_temp"])
        if bed_temp:
            self.metadata.bed_temp = float(bed_temp)

        return self.metadata

    def parse_content(self, content: str, filename: str = "unknown.gcode") -> GCodeMetadata:
        """Parse G-code content string and extract metadata."""
        self.metadata = GCodeMetadata()
        self.metadata.filename = filename

        # Extract estimated time
        time_str = self._extract_match(content, self.PATTERNS["estimated_time"])
        if time_str:
            self.metadata.estimated_time_seconds = self._parse_time_string(time_str)
            self.metadata.estimated_time_formatted = self._format_time(
                self.metadata.estimated_time_seconds
            )

        # Extract other metadata similarly...
        filament_mm = self._extract_match(content, self.PATTERNS["filament_mm"])
        if filament_mm:
            self.metadata.filament_used_mm = float(filament_mm)

        filament_g = self._extract_match(content, self.PATTERNS["filament_grams"])
        if filament_g:
            self.metadata.filament_used_grams = float(filament_g)

        layer_height = self._extract_match(content, self.PATTERNS["layer_height"])
        if layer_height:
            self.metadata.layer_height = float(layer_height)

        total_layers = self._extract_match(content, self.PATTERNS["total_layers"])
        if total_layers:
            self.metadata.total_layers = int(total_layers)

        nozzle_temp = self._extract_match(content, self.PATTERNS["nozzle_temp"])
        if nozzle_temp:
            self.metadata.nozzle_temp = float(nozzle_temp)

        bed_temp = self._extract_match(content, self.PATTERNS["bed_temp"])
        if bed_temp:
            self.metadata.bed_temp = float(bed_temp)

        return self.metadata
