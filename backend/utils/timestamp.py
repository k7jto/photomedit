"""Timestamp utilities for event dates."""
from datetime import datetime
from typing import Optional, Dict, Any


def parse_event_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse event date string to datetime."""
    if not date_str:
        return None
    
    # Try various formats
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y-%m',
        '%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:len(fmt)], fmt)
        except (ValueError, IndexError):
            continue
    
    return None


def format_event_date_for_exif(dt: Optional[datetime], precision: str = 'DAY') -> Optional[str]:
    """Format datetime for EXIF fields."""
    if not dt:
        return None
    
    if precision == 'YEAR':
        return dt.strftime('%Y:01:01 00:00:00')
    elif precision == 'MONTH':
        return dt.strftime('%Y:%m:01 00:00:00')
    else:  # DAY or UNKNOWN
        return dt.strftime('%Y:%m:%d %H:%M:%S')

