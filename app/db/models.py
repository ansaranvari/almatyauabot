from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, Float, Integer, Boolean, Text
from geoalchemy2 import Geography
from app.db.database import Base


class User(Base):
    """User model with language preference"""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)  # Telegram user_id
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="ru", nullable=False, index=True)
    is_active = Column(Boolean, default=True)

    # Onboarding flags
    seen_check_onboarding = Column(Boolean, default=False, nullable=False)
    seen_subscribe_onboarding = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, lang={self.language_code})>"


class AirQualityStation(Base):
    """Air quality monitoring station with PostGIS location"""

    __tablename__ = "air_quality_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(255), unique=True, nullable=False, index=True)  # External API station ID
    name = Column(String(255), nullable=False)
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)  # PostGIS geography
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Air quality data
    pm25 = Column(Float, nullable=True)  # PM2.5 µg/m³
    pm10 = Column(Float, nullable=True)  # PM10 µg/m³
    pm1 = Column(Float, nullable=True)   # PM1.0 µg/m³
    aqi = Column(Integer, nullable=True)  # Air Quality Index

    # Environmental data
    temperature = Column(Float, nullable=True)  # Celsius
    humidity = Column(Float, nullable=True)     # Percentage

    # Metadata
    last_measurement_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AirQualityStation(id={self.station_id}, name={self.name})>"


class UserQuery(Base):
    """Log of user queries for analytics"""

    __tablename__ = "user_queries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    nearest_station_id = Column(String(255), nullable=True)
    query_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<UserQuery(user_id={self.user_id}, station={self.nearest_station_id})>"


class Subscription(Base):
    """User subscription to air quality notifications at a specific location"""

    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user_id
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)  # PostGIS geography
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Duration settings
    expiry_date = Column(DateTime, nullable=True)  # Null = Forever, otherwise expiration timestamp

    # Quiet hours settings
    mute_start = Column(Integer, default=23, nullable=False)  # Hour (0-23) when quiet hours start
    mute_end = Column(Integer, default=7, nullable=False)  # Hour (0-23) when quiet hours end

    # Notification tracking
    last_notified_at = Column(DateTime, nullable=True)  # When user was last notified
    last_aqi_level = Column(Integer, nullable=True)  # Last known AQI to detect transitions

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, lat={self.latitude}, lon={self.longitude})>"


class SafetyNetSession(Base):
    """Temporary session for reverse monitoring (alert when air gets bad)"""

    __tablename__ = "safety_net_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user_id
    subscription_id = Column(BigInteger, nullable=False, index=True)  # Reference to subscription

    # Session parameters
    start_aqi = Column(Integer, nullable=False)  # Baseline AQI when session started
    session_expiry = Column(DateTime, nullable=False, index=True)  # When session expires (3 hours)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SafetyNetSession(user_id={self.user_id}, start_aqi={self.start_aqi})>"


class FavoriteLocation(Base):
    """User's saved favorite locations for quick air quality checks"""

    __tablename__ = "favorite_locations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram user_id
    name = Column(String(100), nullable=False)  # User-defined name (e.g. "Home", "Work")
    location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)  # PostGIS geography
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<FavoriteLocation(user_id={self.user_id}, name={self.name})>"


class AirQualityReading(Base):
    """Historical air quality readings for trend analysis"""

    __tablename__ = "air_quality_readings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    station_id = Column(String(255), nullable=False, index=True)  # External API station ID

    # Air quality data snapshot
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    pm1 = Column(Float, nullable=True)
    aqi = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)

    # Timestamp for this reading
    measured_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AirQualityReading(station_id={self.station_id}, aqi={self.aqi}, measured_at={self.measured_at})>"
