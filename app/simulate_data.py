#!/usr/bin/env python3
"""Simulate 24 hours of air quality data for a station"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, '/app')
os.chdir('/app')

from app.db.database import AsyncSessionLocal
from app.db.models import AirQualityReading
from app.utils.air_quality import calculate_aqi_pm25

async def simulate_24h_data(station_id: str):
    """Generate realistic 24-hour data for a station"""

    # Base values with realistic variation
    base_pm25 = 20  # Starting PM2.5 value
    base_pm10 = 35  # Starting PM10 value
    base_pm1 = 12   # Starting PM1 value
    base_temp = 5   # Base temperature in Celsius
    base_humidity = 65  # Base humidity percentage

    readings = []
    now = datetime.utcnow()

    # Generate hourly readings for the past 24 hours
    for hour_offset in range(24, 0, -1):
        # Calculate timestamp
        timestamp = now - timedelta(hours=hour_offset)

        # Create realistic variations throughout the day
        # Air quality typically worse in morning (6-9) and evening (18-21)
        hour_of_day = timestamp.hour

        # Morning and evening peaks
        if 6 <= hour_of_day <= 9:
            traffic_factor = 1.5  # Morning rush hour
        elif 18 <= hour_of_day <= 21:
            traffic_factor = 1.7  # Evening rush hour
        elif 0 <= hour_of_day <= 5:
            traffic_factor = 0.7  # Night time - cleaner air
        else:
            traffic_factor = 1.0  # Normal daytime

        # Add random variation
        variation = random.uniform(0.8, 1.2)

        # Calculate pollutant values
        pm25 = max(1, base_pm25 * traffic_factor * variation + random.uniform(-5, 5))
        pm10 = max(1, base_pm10 * traffic_factor * variation + random.uniform(-8, 8))
        pm1 = max(1, base_pm1 * traffic_factor * variation + random.uniform(-3, 3))

        # Calculate AQI from PM2.5
        aqi = calculate_aqi_pm25(pm25)

        # Temperature and humidity variations
        # Temperature cooler at night, warmer during day
        if 12 <= hour_of_day <= 16:
            temp = base_temp + random.uniform(3, 6)  # Afternoon warmth
        elif 0 <= hour_of_day <= 6:
            temp = base_temp + random.uniform(-5, -2)  # Night cold
        else:
            temp = base_temp + random.uniform(-1, 2)

        humidity = base_humidity + random.uniform(-10, 10)

        reading = AirQualityReading(
            station_id=station_id,
            pm25=round(pm25, 1),
            pm10=round(pm10, 1),
            pm1=round(pm1, 1),
            aqi=int(aqi),
            temperature=round(temp, 1),
            humidity=round(humidity, 1),
            measured_at=timestamp
        )
        readings.append(reading)

        print(f"Generated: {timestamp.strftime('%Y-%m-%d %H:%M')} - PM2.5: {reading.pm25:.1f}, AQI: {reading.aqi}, Temp: {reading.temperature:.1f}°C")

    # Insert into database
    async with AsyncSessionLocal() as db:
        try:
            # Delete existing readings for this station from past 24 hours
            from sqlalchemy import delete
            since = now - timedelta(hours=24)
            await db.execute(
                delete(AirQualityReading).where(
                    AirQualityReading.station_id == station_id,
                    AirQualityReading.measured_at >= since
                )
            )

            # Add new simulated readings
            for reading in readings:
                db.add(reading)

            await db.commit()
            print(f"\n✅ Successfully generated and saved {len(readings)} readings for station {station_id}")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")
            raise

async def main():
    station_id = "167593"  # №4 Qalalyq emhana (Orbita 3)
    print(f"Generating 24 hours of simulated data for station {station_id}...\n")
    await simulate_24h_data(station_id)

if __name__ == "__main__":
    asyncio.run(main())
