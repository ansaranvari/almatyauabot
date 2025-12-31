"""Air quality calculation utilities"""


def calculate_aqi_pm25(pm25: float) -> int:
    """
    Calculate AQI from PM2.5 concentration using US EPA standard

    Args:
        pm25: PM2.5 concentration in µg/m³

    Returns:
        AQI value (0-500)
    """
    if pm25 < 0:
        return 0

    # AQI breakpoints for PM2.5
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]

    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= pm25 <= c_high:
            # Linear interpolation formula
            aqi = ((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low
            return round(aqi)

    # If concentration exceeds all breakpoints
    return 500


def get_aqi_category(aqi: int) -> tuple[str, str]:
    """
    Get AQI category and emoji

    Args:
        aqi: AQI value

    Returns:
        Tuple of (status_key, emoji)
    """
    if aqi <= 50:
        return ("status_good", "🟢")
    elif aqi <= 100:
        return ("status_moderate", "🟡")
    elif aqi <= 150:
        return ("status_unhealthy_sensitive", "🟠")
    elif aqi <= 200:
        return ("status_unhealthy", "🔴")
    elif aqi <= 300:
        return ("status_very_unhealthy", "🟣")
    else:
        return ("status_hazardous", "🟤")


def get_health_advice_key(aqi: int) -> str:
    """
    Get health advice key based on AQI

    Args:
        aqi: AQI value

    Returns:
        Localization key for health advice
    """
    if aqi <= 50:
        return "advice_good"
    elif aqi <= 100:
        return "advice_moderate"
    elif aqi <= 150:
        return "advice_unhealthy_sensitive"
    elif aqi <= 200:
        return "advice_unhealthy"
    elif aqi <= 300:
        return "advice_very_unhealthy"
    else:
        return "advice_hazardous"
