"""Chart generation service for air quality trends"""
import io
import logging
from datetime import datetime, timedelta
from typing import Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AirQualityReading
from app.utils.redis_client import redis_cache

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generate air quality trend charts"""

    @staticmethod
    def get_aqi_color(aqi: Optional[int]) -> str:
        """Get color for AQI value"""
        if aqi is None:
            return '#CCCCCC'
        if aqi <= 50:
            return '#00E400'  # Green - Good
        elif aqi <= 100:
            return '#FFFF00'  # Yellow - Moderate
        elif aqi <= 150:
            return '#FF7E00'  # Orange - Unhealthy for Sensitive Groups
        elif aqi <= 200:
            return '#FF0000'  # Red - Unhealthy
        elif aqi <= 300:
            return '#8F3F97'  # Purple - Very Unhealthy
        else:
            return '#7E0023'  # Maroon - Hazardous

    async def generate_24h_chart(
        self,
        db: AsyncSession,
        station_id: str,
        station_name: str,
        lang: str = "ru"
    ) -> Optional[bytes]:
        """
        Generate 24-hour AQI trend chart for a station

        Args:
            db: Database session
            station_id: Station ID to generate chart for
            station_name: Station name for chart title
            lang: Language code (ru/kk)

        Returns:
            PNG image bytes or None if insufficient data
        """
        try:
            # Check cache first (1 hour TTL)
            cache_key = f"chart:24h:{station_id}:{lang}"
            cached_chart = await redis_cache.get(cache_key)
            if cached_chart:
                logger.info(f"Serving cached chart for station {station_id}")
                return cached_chart
            # Fetch last 24 hours of readings
            now = datetime.utcnow()
            since = now - timedelta(hours=24)

            result = await db.execute(
                select(AirQualityReading)
                .where(
                    AirQualityReading.station_id == station_id,
                    AirQualityReading.measured_at >= since
                )
                .order_by(AirQualityReading.measured_at.asc())
            )
            readings = result.scalars().all()

            if len(readings) < 2:
                logger.warning(f"Insufficient data for chart: {len(readings)} readings")
                return None

            # Extract data
            timestamps = [r.measured_at for r in readings]
            aqi_values = [r.aqi if r.aqi is not None else 0 for r in readings]

            # Create figure
            plt.figure(figsize=(12, 6), facecolor='white')
            ax = plt.gca()

            # Plot AQI line
            ax.plot(timestamps, aqi_values, color='#2C3E50', linewidth=2, marker='o', markersize=4)

            # Fill area under curve with AQI colors
            # Split into segments based on AQI ranges
            for i in range(len(timestamps) - 1):
                t1, t2 = timestamps[i], timestamps[i + 1]
                aqi1, aqi2 = aqi_values[i], aqi_values[i + 1]
                avg_aqi = (aqi1 + aqi2) / 2
                color = self.get_aqi_color(int(avg_aqi))
                ax.fill_between([t1, t2], [aqi1, aqi2], alpha=0.3, color=color)

            # Formatting
            title = f"{'График качества воздуха за 24 часа' if lang == 'ru' else 'Ауа сапасының 24 сағаттық графигі'}\n{station_name}"
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

            xlabel = 'Время' if lang == 'ru' else 'Уақыт'
            ylabel = 'Индекс качества воздуха (AQI)' if lang == 'ru' else 'Ауа сапасы индексі (AQI)'
            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)

            # Format x-axis to show hours
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
            plt.xticks(rotation=45, ha='right')

            # Add AQI level reference lines
            ax.axhline(y=50, color='#00E400', linestyle='--', alpha=0.5, linewidth=1)
            ax.axhline(y=100, color='#FFFF00', linestyle='--', alpha=0.5, linewidth=1)
            ax.axhline(y=150, color='#FF7E00', linestyle='--', alpha=0.5, linewidth=1)

            # Add legend for AQI levels
            if lang == 'ru':
                legend_labels = [
                    'Чистый (0-50)',
                    'Умеренно (51-100)',
                    'Вредно для чувствит. (101-150)'
                ]
            else:
                legend_labels = [
                    'Таза (0-50)',
                    'Орташа (51-100)',
                    'Сезімталдарға зиянды (101-150)'
                ]

            legend_colors = ['#00E400', '#FFFF00', '#FF7E00']
            handles = [plt.Line2D([0], [0], color=c, linewidth=2) for c in legend_colors]
            ax.legend(handles, legend_labels, loc='upper right', fontsize=9)

            # Grid
            ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)

            # Tight layout
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            image_bytes = buf.getvalue()
            buf.close()

            plt.close()

            # Cache the generated chart for 1 hour (3600 seconds)
            await redis_cache.set(cache_key, image_bytes, expire=3600)

            logger.info(f"Generated 24h chart for station {station_id} with {len(readings)} data points")
            return image_bytes

        except Exception as e:
            logger.error(f"Error generating chart for station {station_id}: {e}", exc_info=True)
            return None


# Global instance
chart_generator = ChartGenerator()
