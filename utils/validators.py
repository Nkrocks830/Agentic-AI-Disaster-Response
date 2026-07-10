"""
ResQNet AI - Input Validators
"""

import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """Basic phone number validation (India format)."""
    cleaned = re.sub(r"[\s\-\+\(\)]", "", phone)
    return len(cleaned) >= 10 and cleaned.isdigit()


def validate_coordinates(lat: float, lon: float,
                          lat_min: float = -90, lat_max: float = 90,
                          lon_min: float = -180, lon_max: float = 180) -> bool:
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def validate_chennai_coords(lat: float, lon: float) -> bool:
    """Check if coordinates are within Chennai metropolitan area."""
    return 12.7 <= lat <= 13.3 and 79.8 <= lon <= 80.6


def validate_emergency_description(text: str, min_length: int = 10) -> Optional[str]:
    """Returns error string if invalid, None if valid."""
    if not text or len(text.strip()) < min_length:
        return f"Description must be at least {min_length} characters."
    return None
