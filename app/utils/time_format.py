"""Time formatting utilities for relative time display"""
from datetime import datetime, timedelta


def get_relative_time(measurement_time: datetime, lang: str) -> str:
    """
    Format measurement time as relative time (e.g., "Час назад")

    Args:
        measurement_time: UTC datetime of measurement
        lang: Language code (ru/kk)

    Returns:
        Relative time string
    """
    # Current time in UTC
    now = datetime.utcnow()

    # Calculate time difference
    delta = now - measurement_time
    total_minutes = int(delta.total_seconds() / 60)
    total_hours = int(delta.total_seconds() / 3600)
    total_days = delta.days

    # Less than 1 minute
    if total_minutes < 1:
        return "Только что" if lang == "ru" else "Жаңа ғана"

    # Less than 1 hour - show minutes
    if total_minutes < 60:
        if lang == "ru":
            return format_minutes_ru(total_minutes)
        else:
            return format_minutes_kk(total_minutes)

    # Less than 24 hours - show hours
    if total_hours < 24:
        if lang == "ru":
            return format_hours_ru(total_hours)
        else:
            return format_hours_kk(total_hours)

    # 24+ hours - show absolute time with date
    # Convert to Almaty time (UTC+5)
    local_time = measurement_time + timedelta(hours=5)
    return local_time.strftime("%d.%m.%y %H:%M")


def format_minutes_ru(minutes: int) -> str:
    """Format minutes in Russian with proper plural forms"""
    if minutes % 10 == 1 and minutes % 100 != 11:
        return f"{minutes} минуту назад"
    elif 2 <= minutes % 10 <= 4 and (minutes % 100 < 10 or minutes % 100 >= 20):
        return f"{minutes} минуты назад"
    else:
        return f"{minutes} минут назад"


def format_hours_ru(hours: int) -> str:
    """Format hours in Russian with proper plural forms"""
    if hours % 10 == 1 and hours % 100 != 11:
        return f"{hours} час назад"
    elif 2 <= hours % 10 <= 4 and (hours % 100 < 10 or hours % 100 >= 20):
        return f"{hours} часа назад"
    else:
        return f"{hours} часов назад"


def format_minutes_kk(minutes: int) -> str:
    """Format minutes in Kazakh"""
    return f"{minutes} минут бұрын"


def format_hours_kk(hours: int) -> str:
    """Format hours in Kazakh"""
    return f"{hours} сағат бұрын"
