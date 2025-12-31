import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_MakePoint
from app.db.models import AirQualityStation, AirQualityReading
from app.db.database import AsyncSessionLocal
from app.core.config import get_settings
from app.utils.air_quality import calculate_aqi_pm25

settings = get_settings()
logger = logging.getLogger(__name__)


class AirQualityDataSync:
    """Background service for syncing air quality data from API"""

    def __init__(self):
        self.api_url = settings.AIR_API_URL
        self.stations_api_url = "https://api.air.org.kz/api/stations"
        self.station_names_cache = {}  # Cache for station ID -> name mapping

    async def fetch_station_names(self) -> Dict[str, str]:
        """
        Fetch station metadata and create ID -> name mapping

        Returns:
            Dictionary mapping station IDs to names
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.stations_api_url)
                response.raise_for_status()
                stations = response.json()

                # Create mapping of ID to name
                station_map = {}
                if isinstance(stations, list):
                    for station in stations:
                        station_id = str(station.get("id", ""))
                        station_name = station.get("name", "")
                        if station_id and station_name:
                            station_map[station_id] = station_name

                    logger.info(f"Fetched {len(station_map)} station names")
                    return station_map
                else:
                    logger.warning(f"Unexpected stations API format: {type(stations)}")
                    return {}

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching station names: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching station names: {e}")
            return {}

    async def fetch_stations_data(self) -> List[Dict[str, Any]]:
        """
        Fetch latest data from air.org.kz API

        Returns:
            List of station data dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.api_url)
                response.raise_for_status()
                data = response.json()

                # The API returns an array of station data
                if isinstance(data, list):
                    logger.info(f"Fetched {len(data)} stations from API")
                    return data
                else:
                    logger.warning(f"Unexpected API response format: {type(data)}")
                    return []

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching air quality data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching air quality data: {e}")
            return []

    async def sync_station_data(self, db: AsyncSession, station_data: Dict[str, Any], station_names: Dict[str, str]):
        """
        Sync single station data to database

        Args:
            db: Database session
            station_data: Station data from API
            station_names: Mapping of station IDs to names
        """
        try:
            # Extract data from API response
            # Use locationid (stable) instead of id (changes hourly)
            station_id = station_data.get("locationid") or station_data.get("id")
            if not station_id:
                logger.warning(f"Station without ID: {station_data}")
                return

            # Get station name from locationname field in API response
            # Fallback to stations API mapping if not available
            name = station_data.get("locationname")
            if not name or name.strip() == "":
                station_id_str = str(station_id)
                name = station_names.get(station_id_str, f"Датчик {station_id}")

            latitude = station_data.get("latitude") or station_data.get("lat")
            longitude = station_data.get("longitude") or station_data.get("lon")

            if latitude is None or longitude is None:
                logger.warning(f"Station {station_id} missing coordinates")
                return

            # Air quality measurements
            pm25 = station_data.get("pm25") or station_data.get("pm02")
            pm10 = station_data.get("pm10")
            pm1 = station_data.get("pm01") or station_data.get("pm1")

            # Calculate AQI
            aqi = None
            if pm25 is not None:
                aqi = calculate_aqi_pm25(float(pm25))

            # Environmental data
            temperature = station_data.get("temperature") or station_data.get("temp")
            humidity = station_data.get("humidity") or station_data.get("hum")

            # Timestamp - convert to timezone-naive UTC datetime
            last_measurement = station_data.get("timestamp") or station_data.get("lastUpdate")
            if last_measurement:
                if isinstance(last_measurement, str):
                    try:
                        # Parse ISO format with timezone (e.g., "2025-12-22T23:00:00+05:00")
                        dt = datetime.fromisoformat(last_measurement.replace('Z', '+00:00'))
                        # Convert to UTC if timezone-aware, then make naive for database storage
                        if dt.tzinfo is not None:
                            # Convert to UTC and remove timezone info
                            last_measurement = dt.astimezone(timezone.utc).replace(tzinfo=None)
                        else:
                            # Already naive, assume it's UTC
                            last_measurement = dt
                    except:
                        last_measurement = datetime.utcnow()
            else:
                last_measurement = datetime.utcnow()

            # Check if station exists
            result = await db.execute(
                select(AirQualityStation).where(AirQualityStation.station_id == str(station_id))
            )
            station = result.scalar_one_or_none()

            if station:
                # Update existing station
                station.name = name
                station.latitude = float(latitude)
                station.longitude = float(longitude)
                station.location = func.ST_SetSRID(ST_MakePoint(float(longitude), float(latitude)), 4326)
                station.pm25 = float(pm25) if pm25 is not None else None
                station.pm10 = float(pm10) if pm10 is not None else None
                station.pm1 = float(pm1) if pm1 is not None else None
                station.aqi = aqi
                station.temperature = float(temperature) if temperature is not None else None
                station.humidity = float(humidity) if humidity is not None else None
                station.last_measurement_at = last_measurement
                station.updated_at = datetime.utcnow()

                logger.debug(f"Updated station {station_id}")
            else:
                # Create new station
                station = AirQualityStation(
                    station_id=str(station_id),
                    name=name,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    location=func.ST_SetSRID(ST_MakePoint(float(longitude), float(latitude)), 4326),
                    pm25=float(pm25) if pm25 is not None else None,
                    pm10=float(pm10) if pm10 is not None else None,
                    pm1=float(pm1) if pm1 is not None else None,
                    aqi=aqi,
                    temperature=float(temperature) if temperature is not None else None,
                    humidity=float(humidity) if humidity is not None else None,
                    last_measurement_at=last_measurement,
                )
                db.add(station)
                logger.debug(f"Created new station {station_id}")

            # Save historical reading for trend analysis
            reading = AirQualityReading(
                station_id=str(station_id),
                pm25=float(pm25) if pm25 is not None else None,
                pm10=float(pm10) if pm10 is not None else None,
                pm1=float(pm1) if pm1 is not None else None,
                aqi=aqi,
                temperature=float(temperature) if temperature is not None else None,
                humidity=float(humidity) if humidity is not None else None,
                measured_at=last_measurement
            )
            db.add(reading)
            logger.debug(f"Saved historical reading for station {station_id}")

        except Exception as e:
            logger.error(f"Error syncing station {station_data.get('id', 'unknown')}: {e}")

    async def cleanup_old_readings(self, db: AsyncSession):
        """Delete readings older than 24 hours to save storage"""
        try:
            from sqlalchemy import delete
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            result = await db.execute(
                delete(AirQualityReading).where(
                    AirQualityReading.measured_at < cutoff_time
                )
            )

            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} readings older than 24 hours")

        except Exception as e:
            logger.error(f"Error cleaning up old readings: {e}")

    async def run_sync(self):
        """Run synchronization process"""
        logger.info("Starting air quality data synchronization")

        # Fetch station names mapping
        station_names = await self.fetch_station_names()
        if not station_names:
            logger.warning("No station names fetched, using default names")

        # Fetch data from API
        stations_data = await self.fetch_stations_data()

        if not stations_data:
            logger.warning("No station data fetched")
            return

        # Sync to database
        async with AsyncSessionLocal() as db:
            try:
                # Clean up old readings first
                await self.cleanup_old_readings(db)

                for station_data in stations_data:
                    await self.sync_station_data(db, station_data, station_names)

                await db.commit()
                logger.info(f"Successfully synced {len(stations_data)} stations")

            except Exception as e:
                await db.rollback()
                logger.error(f"Error during sync transaction: {e}")
                raise

    async def start_scheduler(self):
        """Start periodic sync scheduler - syncs at :10 and :15 of each hour to account for API delay"""
        logger.info("Starting hourly sync scheduler (syncs at :10 and :15 of each hour)")

        while True:
            # Calculate seconds until next sync time (:10 or :15)
            now = datetime.utcnow()
            current_minute = now.minute
            current_second = now.second

            # Determine next sync minute
            if current_minute < 10:
                next_sync_minute = 10
                wait_minutes = 10 - current_minute
            elif current_minute < 15:
                next_sync_minute = 15
                wait_minutes = 15 - current_minute
            elif current_minute < 60:
                next_sync_minute = 10
                wait_minutes = 60 - current_minute + 10
            else:
                next_sync_minute = 10
                wait_minutes = 10

            # Calculate total wait time in seconds
            wait_seconds = (wait_minutes * 60) - current_second

            logger.info(f"Next sync at :{next_sync_minute:02d}, waiting {wait_seconds} seconds")
            await asyncio.sleep(wait_seconds)

            try:
                await self.run_sync()
            except Exception as e:
                logger.error(f"Sync task failed: {e}")


# Global sync instance
data_sync = AirQualityDataSync()
