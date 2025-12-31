from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Distance, ST_MakePoint
from app.db.models import AirQualityStation, UserQuery
from app.utils.air_quality import calculate_aqi_pm25, get_aqi_category, get_health_advice_key
from app.utils.time_format import get_relative_time
from app.core.locales import get_text


class AirQualityService:
    """Service for air quality operations"""

    @staticmethod
    async def find_nearest_station(
        db: AsyncSession,
        latitude: float,
        longitude: float,
        max_distance_km: float = 50.0
    ) -> Optional[AirQualityStation]:
        """
        Find nearest air quality station using PostGIS

        Args:
            db: Database session
            latitude: User's latitude
            longitude: User's longitude
            max_distance_km: Maximum search radius in kilometers

        Returns:
            Nearest station or None
        """
        # Create point from user coordinates (SRID 4326 = WGS84)
        user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

        # Only consider stations with measurements within last 2.5 hours (account for API delays)
        from datetime import datetime, timedelta
        max_measurement_age = datetime.utcnow() - timedelta(minutes=150)

        # Query for nearest station within max distance
        query = (
            select(
                AirQualityStation,
                ST_Distance(
                    AirQualityStation.location,
                    func.cast(user_point, type_=AirQualityStation.location.type)
                ).label("distance")
            )
            .where(
                ST_Distance(
                    AirQualityStation.location,
                    func.cast(user_point, type_=AirQualityStation.location.type)
                ) <= max_distance_km * 1000,  # Convert km to meters
                AirQualityStation.last_measurement_at >= max_measurement_age  # Only fresh measurements
            )
            .order_by(text("distance"))
            .limit(1)
        )

        result = await db.execute(query)
        row = result.first()

        if row:
            return row[0]  # Return the station object
        return None

    @staticmethod
    async def log_user_query(
        db: AsyncSession,
        user_id: int,
        latitude: float,
        longitude: float,
        station_id: Optional[str] = None
    ):
        """
        Log user query for analytics

        Args:
            db: Database session
            user_id: Telegram user ID
            latitude: Query latitude
            longitude: Query longitude
            station_id: Nearest station ID (if found)
        """
        query = UserQuery(
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            nearest_station_id=station_id,
            query_timestamp=datetime.utcnow()
        )
        db.add(query)
        await db.commit()

    @staticmethod
    def format_air_quality_message(station: AirQualityStation, distance_km: float, lang: str) -> str:
        """
        Format air quality data into a localized message

        Args:
            station: Air quality station object
            distance_km: Distance to station in km
            lang: Language code (ru/kk)

        Returns:
            Formatted message with HTML markup
        """
        # Calculate AQI if not present
        aqi = station.aqi
        if not aqi and station.pm25:
            aqi = calculate_aqi_pm25(station.pm25)

        # Get status and emoji
        status_key, emoji = get_aqi_category(aqi) if aqi else ("status_good", "⚪")

        # Build message in new format
        message_parts = []

        # 1. Status line
        status_line = get_text(lang, "status_line", emoji=emoji, status=get_text(lang, status_key))
        message_parts.append(status_line)
        message_parts.append("")  # Empty line

        # 2. AQI and PM levels
        if aqi:
            aqi_line = get_text(lang, "aqi_line", aqi=aqi)
            message_parts.append(aqi_line)

        pm_data = []
        if station.pm25 is not None:
            pm_data.append(get_text(lang, "pm25_label", value=f"{station.pm25:.1f}"))
        if station.pm10 is not None:
            pm_data.append(get_text(lang, "pm10_label", value=f"{station.pm10:.1f}"))
        if station.pm1 is not None:
            pm_data.append(get_text(lang, "pm1_label", value=f"{station.pm1:.1f}"))

        if pm_data:
            message_parts.extend(pm_data)

        message_parts.append("")  # Empty line

        # 3. Station info (name, distance, time)
        station_name = get_text(lang, "station_name", name=station.name)
        message_parts.append(station_name)

        # Format distance: meters if < 1 km, otherwise km
        if distance_km < 1.0:
            distance_meters = int(distance_km * 1000)
            distance_line = get_text(lang, "distance_line_m", distance=distance_meters)
        else:
            distance_line = get_text(lang, "distance_line_km", distance=f"{distance_km:.2f}")
        message_parts.append(distance_line)

        if station.last_measurement_at:
            # Get relative time (e.g., "Час назад")
            time_str = get_relative_time(station.last_measurement_at, lang)
            update_line = get_text(lang, "update_line", time=time_str)
            message_parts.append(update_line)

        # Temperature and humidity (optional)
        env_data = []
        if station.temperature is not None:
            env_data.append(get_text(lang, "temp_label", value=f"{station.temperature:.1f}"))
        if station.humidity is not None:
            env_data.append(get_text(lang, "humidity_label", value=f"{station.humidity:.0f}"))

        if env_data:
            message_parts.append(" | ".join(env_data))

        message_parts.append("")  # Empty line

        # 4. Health advice
        if aqi:
            advice_key = get_health_advice_key(aqi)
            advice_header = get_text(lang, "advice_header_new")
            message_parts.append(advice_header)
            message_parts.append(get_text(lang, advice_key))

        return "\n".join(message_parts)
