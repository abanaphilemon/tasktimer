"""
Utility functions for TaskTimer application.
"""

from datetime import timedelta
from typing import Optional


def format_duration(seconds: float) -> str:
    """
    Format duration as HH:MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "01:23:45"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_duration_human(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h 23m 45s"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def parse_duration(duration_str: str) -> Optional[float]:
    """
    Parse duration string to seconds.

    Args:
        duration_str: Duration string like "1h 30m" or "90m"

    Returns:
        Duration in seconds, or None if parsing fails
    """
    total = 0
    parts = duration_str.lower().split()

    for part in parts:
        if part.endswith('h'):
            try:
                total += int(part[:-1]) * 3600
            except ValueError:
                pass
        elif part.endswith('m'):
            try:
                total += int(part[:-1]) * 60
            except ValueError:
                pass
        elif part.endswith('s'):
            try:
                total += int(part[:-1])
            except ValueError:
                pass
        else:
            try:
                total += int(part)
            except ValueError:
                pass

    return total if total > 0 else None


def format_timestamp(dt, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.

    Args:
        dt: Datetime object
        format_str: Format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        Formatted string
    """
    return dt.strftime(format_str)


def get_time_ago(dt) -> str:
    """
    Get human-readable time ago string.

    Args:
        dt: Datetime object

    Returns:
        String like "2 hours ago"
    """
    from datetime import datetime
    delta = datetime.now() - dt

    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"

    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    minutes = (delta.seconds % 3600) // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"

    return "Just now"
