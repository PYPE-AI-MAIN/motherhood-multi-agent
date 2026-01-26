"""
Date helper functions
"""

from datetime import datetime, timedelta


def get_today() -> str:
    """Get today's date in YYYY-MM-DD format"""
    return datetime.now().strftime("%Y-%m-%d")


def get_tomorrow() -> str:
    """Get tomorrow's date in YYYY-MM-DD format"""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%Y-%m-%d")


def add_days(date_str: str, days: int) -> str:
    """
    Add days to a date string
    
    Args:
        date_str: Date in YYYY-MM-DD format
        days: Number of days to add
    
    Returns:
        New date in YYYY-MM-DD format
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    new_date = date + timedelta(days=days)
    return new_date.strftime("%Y-%m-%d")


def format_date_natural(date_str: str) -> str:
    """
    Format date naturally for speech
    
    Args:
        date_str: Date in YYYY-MM-D format
    
    Returns:
        Natural format like "Monday, January 20"
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%A, %B %d")


def get_day_name(date_str: str) -> str:
    """Get day name from date string"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%A")
