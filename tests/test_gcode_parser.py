"""
Test the G-code parser with the sample file.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from gcode_parser import GCodeParser


def test_parse_sample_gcode():
    """Test parsing the sample G-code file."""
    parser = GCodeParser()
    sample_path = Path(__file__).parent / "sample.gcode"

    metadata = parser.parse_file(str(sample_path))

    print("G-code Parser Test Results")
    print("=" * 40)
    print(f"Filename: {metadata.filename}")
    print(f"Estimated Time (seconds): {metadata.estimated_time_seconds}")
    print(f"Estimated Time (formatted): {metadata.estimated_time_formatted}")
    print(f"Filament Used (mm): {metadata.filament_used_mm}")
    print(f"Filament Used (g): {metadata.filament_used_grams}")
    print(f"Layer Height: {metadata.layer_height}")
    print(f"Total Layers: {metadata.total_layers}")
    print(f"Nozzle Temp: {metadata.nozzle_temp}")
    print(f"Bed Temp: {metadata.bed_temp}")
    print("=" * 40)

    # Verify expected values
    assert metadata.estimated_time_seconds == 9045, f"Expected 9045s, got {metadata.estimated_time_seconds}"
    assert metadata.estimated_time_formatted == "02:30:45", f"Expected 02:30:45, got {metadata.estimated_time_formatted}"
    assert metadata.filament_used_mm == 12345.67, f"Expected 12345.67mm, got {metadata.filament_used_mm}"
    assert metadata.filament_used_grams == 37.5, f"Expected 37.5g, got {metadata.filament_used_grams}"
    assert metadata.layer_height == 0.2, f"Expected 0.2, got {metadata.layer_height}"
    assert metadata.total_layers == 150, f"Expected 150, got {metadata.total_layers}"
    assert metadata.nozzle_temp == 210, f"Expected 210, got {metadata.nozzle_temp}"
    assert metadata.bed_temp == 60, f"Expected 60, got {metadata.bed_temp}"

    print("\nAll assertions passed!")
    return True


def test_time_parsing():
    """Test various time format parsing."""
    parser = GCodeParser()

    test_cases = [
        ("1h 30m 45s", 5445),
        ("2h 30m", 9000),
        ("45m 30s", 2730),
        ("3600", 3600),
        ("01:30:00", 5400),
        ("1d 2h 30m", 95400),
    ]

    print("\nTime Parsing Tests")
    print("=" * 40)

    for time_str, expected in test_cases:
        result = parser._parse_time_string(time_str)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] '{time_str}' -> {result} (expected {expected})")
        assert result == expected, f"Time parsing failed for '{time_str}'"

    print("\nAll time parsing tests passed!")
    return True


if __name__ == "__main__":
    test_parse_sample_gcode()
    test_time_parsing()
    print("\n*** ALL TESTS PASSED ***")
