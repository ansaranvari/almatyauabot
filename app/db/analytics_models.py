"""
Analytics database models for tracking bot metrics and user behavior
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Boolean, Float, JSON, Index
from app.db.database import Base


class DailyUserStats(Base):
    """Track daily user activity metrics"""

    __tablename__ = "daily_user_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)  # Date of the stats (midnight UTC)

    # User counts
    total_users = Column(Integer, default=0)  # Total registered users
    new_users = Column(Integer, default=0)  # New users registered this day
    active_users = Column(Integer, default=0)  # Users who interacted with bot
    returning_users = Column(Integer, default=0)  # Users who came back after first day

    # Engagement metrics
    total_messages = Column(Integer, default=0)  # Total messages/interactions
    avg_messages_per_user = Column(Float, default=0.0)  # Average interactions per active user

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_daily_stats_date', 'date'),
    )


class FeatureUsageStats(Base):
    """Track usage of different bot features"""

    __tablename__ = "feature_usage_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    feature_name = Column(String(100), nullable=False, index=True)

    # Usage counts
    usage_count = Column(Integer, default=0)  # How many times feature was used
    unique_users = Column(Integer, default=0)  # How many unique users used it

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_feature_usage_date_feature', 'date', 'feature_name'),
    )


class SubscriptionStats(Base):
    """Track subscription-related metrics"""

    __tablename__ = "subscription_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)

    # Subscription counts
    total_subscriptions = Column(Integer, default=0)  # Total active subscriptions
    new_subscriptions = Column(Integer, default=0)  # New subscriptions created
    expired_subscriptions = Column(Integer, default=0)  # Subscriptions that expired
    cancelled_subscriptions = Column(Integer, default=0)  # User-cancelled subscriptions

    # Conversion metrics
    subscription_views = Column(Integer, default=0)  # Users who saw subscription prompt
    subscription_conversions = Column(Integer, default=0)  # Users who subscribed
    conversion_rate = Column(Float, default=0.0)  # Conversion percentage

    # Notification metrics
    notifications_sent = Column(Integer, default=0)
    notifications_delivered = Column(Integer, default=0)
    notifications_failed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_subscription_stats_date', 'date'),
    )


class UserEvent(Base):
    """Track individual user events for detailed analysis"""

    __tablename__ = "user_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # e.g., "check_air", "subscribe", "add_favorite"
    event_data = Column(JSON, nullable=True)  # Additional event metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Session tracking
    session_id = Column(String(50), nullable=True, index=True)  # Group events by session

    __table_args__ = (
        Index('idx_user_events_user_time', 'user_id', 'timestamp'),
        Index('idx_user_events_type_time', 'event_type', 'timestamp'),
    )


class UserRetention(Base):
    """Track user retention cohorts"""

    __tablename__ = "user_retention"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cohort_date = Column(DateTime, nullable=False, index=True)  # Date user first joined
    day_number = Column(Integer, nullable=False)  # Days since joining (0, 1, 7, 30, etc.)

    cohort_size = Column(Integer, default=0)  # How many users joined on cohort_date
    retained_users = Column(Integer, default=0)  # How many came back on day_number
    retention_rate = Column(Float, default=0.0)  # Percentage retained

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_retention_cohort_day', 'cohort_date', 'day_number'),
    )
