"""
Analytics service for tracking bot metrics and user behavior
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.database import AsyncSessionLocal
from app.db.analytics_models import (
    DailyUserStats,
    FeatureUsageStats,
    SubscriptionStats,
    UserEvent,
    UserRetention
)
from app.db.models import User, Subscription

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for tracking and analyzing bot usage"""

    @staticmethod
    async def track_event(
        user_id: int,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ):
        """
        Track a user event

        Args:
            user_id: Telegram user ID
            event_type: Type of event (e.g., "check_air", "subscribe", "add_favorite")
            event_data: Additional event metadata
            session_id: Session identifier for grouping events
        """
        try:
            async with AsyncSessionLocal() as db:
                event = UserEvent(
                    user_id=user_id,
                    event_type=event_type,
                    event_data=event_data or {},
                    session_id=session_id or str(uuid.uuid4()),
                    timestamp=datetime.utcnow()
                )
                db.add(event)
                await db.commit()
                logger.debug(f"Tracked event: {event_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to track event {event_type}: {e}")

    @staticmethod
    async def increment_feature_usage(feature_name: str, user_id: int):
        """
        Increment feature usage counter for today

        Args:
            feature_name: Name of the feature (e.g., "check_air", "subscribe")
            user_id: User who used the feature
        """
        try:
            async with AsyncSessionLocal() as db:
                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                # Get or create today's feature stats
                result = await db.execute(
                    select(FeatureUsageStats).where(
                        FeatureUsageStats.date == today,
                        FeatureUsageStats.feature_name == feature_name
                    )
                )
                stats = result.scalars().first()

                if not stats:
                    stats = FeatureUsageStats(
                        date=today,
                        feature_name=feature_name,
                        usage_count=0,
                        unique_users=0
                    )
                    db.add(stats)

                # Increment usage count
                stats.usage_count += 1

                # Check if this is a new unique user for this feature today
                event_exists = await db.execute(
                    select(UserEvent).where(
                        UserEvent.user_id == user_id,
                        UserEvent.event_type == feature_name,
                        UserEvent.timestamp >= today
                    )
                )
                if not event_exists.scalars().first():
                    stats.unique_users += 1

                await db.commit()
        except Exception as e:
            logger.error(f"Failed to increment feature usage for {feature_name}: {e}")

    @staticmethod
    async def update_daily_stats(target_date: Optional[date] = None):
        """
        Update daily user statistics for a specific date

        Args:
            target_date: Date to archive stats for (defaults to today in UTC)

        This should be run once per day (scheduled task)
        """
        try:
            async with AsyncSessionLocal() as db:
                # Use provided date or default to today
                if target_date:
                    today = datetime.combine(target_date, datetime.min.time())
                else:
                    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                tomorrow = today + timedelta(days=1)
                yesterday = today - timedelta(days=1)

                # Count total users
                total_users_result = await db.execute(select(func.count(User.id)))
                total_users = total_users_result.scalar()

                # Count new users (registered on target day)
                new_users_result = await db.execute(
                    select(func.count(User.id)).where(
                        User.created_at >= today,
                        User.created_at < tomorrow
                    )
                )
                new_users = new_users_result.scalar()

                # Count active users (had events on target day)
                active_users_result = await db.execute(
                    select(func.count(func.distinct(UserEvent.user_id))).where(
                        UserEvent.timestamp >= today,
                        UserEvent.timestamp < tomorrow
                    )
                )
                active_users = active_users_result.scalar()

                # Count returning users (users who were active yesterday and today)
                returning_users_result = await db.execute(
                    select(func.count(func.distinct(UserEvent.user_id))).where(
                        UserEvent.timestamp >= today,
                        UserEvent.timestamp < tomorrow,
                        UserEvent.user_id.in_(
                            select(UserEvent.user_id).where(
                                UserEvent.timestamp >= yesterday,
                                UserEvent.timestamp < today
                            )
                        )
                    )
                )
                returning_users = returning_users_result.scalar()

                # Count total messages on target day
                messages_result = await db.execute(
                    select(func.count(UserEvent.id)).where(
                        UserEvent.timestamp >= today,
                        UserEvent.timestamp < tomorrow
                    )
                )
                total_messages = messages_result.scalar()

                # Count air quality checks on target day
                air_checks_result = await db.execute(
                    select(func.count(UserEvent.id)).where(
                        UserEvent.timestamp >= today,
                        UserEvent.timestamp < tomorrow,
                        UserEvent.event_type == 'check_air_clicked'
                    )
                )
                air_checks = air_checks_result.scalar() or 0

                # Count unique users who checked air quality
                unique_air_checkers_result = await db.execute(
                    select(func.count(func.distinct(UserEvent.user_id))).where(
                        UserEvent.timestamp >= today,
                        UserEvent.timestamp < tomorrow,
                        UserEvent.event_type == 'check_air_clicked'
                    )
                )
                unique_air_checkers = unique_air_checkers_result.scalar() or 0

                # Calculate average messages per user
                avg_messages = total_messages / active_users if active_users > 0 else 0

                # Create or update stats
                result = await db.execute(
                    select(DailyUserStats).where(DailyUserStats.date == today)
                )
                stats = result.scalars().first()

                if not stats:
                    stats = DailyUserStats(date=today)
                    db.add(stats)

                stats.total_users = total_users
                stats.new_users = new_users
                stats.active_users = active_users
                stats.returning_users = returning_users
                stats.total_messages = total_messages
                stats.avg_messages_per_user = avg_messages
                stats.air_checks = air_checks
                stats.unique_air_checkers = unique_air_checkers

                await db.commit()
                logger.info(f"Updated daily stats for {today.strftime('%Y-%m-%d')}: {active_users} active users, {new_users} new users, {air_checks} air checks")
        except Exception as e:
            logger.error(f"Failed to update daily stats: {e}", exc_info=True)

    @staticmethod
    async def update_subscription_stats():
        """
        Update subscription statistics for today

        This should be run periodically throughout the day
        """
        try:
            async with AsyncSessionLocal() as db:
                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                # Count total active subscriptions
                total_subs_result = await db.execute(
                    select(func.count(Subscription.id)).where(
                        Subscription.is_active == True
                    )
                )
                total_subscriptions = total_subs_result.scalar()

                # Count new subscriptions today
                new_subs_result = await db.execute(
                    select(func.count(Subscription.id)).where(
                        Subscription.created_at >= today
                    )
                )
                new_subscriptions = new_subs_result.scalar()

                # Count expired subscriptions today
                expired_subs_result = await db.execute(
                    select(func.count(Subscription.id)).where(
                        Subscription.expires_at >= today,
                        Subscription.expires_at < today + timedelta(days=1),
                        Subscription.is_active == False
                    )
                )
                expired_subscriptions = expired_subs_result.scalar()

                # Count subscription views (subscription_prompt events)
                views_result = await db.execute(
                    select(func.count(UserEvent.id)).where(
                        UserEvent.event_type == "subscription_prompt",
                        UserEvent.timestamp >= today
                    )
                )
                subscription_views = views_result.scalar()

                # Count subscription conversions (subscription_created events)
                conversions_result = await db.execute(
                    select(func.count(UserEvent.id)).where(
                        UserEvent.event_type == "subscription_created",
                        UserEvent.timestamp >= today
                    )
                )
                subscription_conversions = conversions_result.scalar()

                # Calculate conversion rate
                conversion_rate = (
                    (subscription_conversions / subscription_views * 100)
                    if subscription_views > 0 else 0
                )

                # Get or create today's subscription stats
                result = await db.execute(
                    select(SubscriptionStats).where(SubscriptionStats.date == today)
                )
                stats = result.scalars().first()

                if not stats:
                    stats = SubscriptionStats(date=today)
                    db.add(stats)

                stats.total_subscriptions = total_subscriptions
                stats.new_subscriptions = new_subscriptions
                stats.expired_subscriptions = expired_subscriptions
                stats.subscription_views = subscription_views
                stats.subscription_conversions = subscription_conversions
                stats.conversion_rate = conversion_rate

                await db.commit()
                logger.info(f"Updated subscription stats: {total_subscriptions} active, {new_subscriptions} new")
        except Exception as e:
            logger.error(f"Failed to update subscription stats: {e}", exc_info=True)

    @staticmethod
    async def calculate_retention(cohort_days: list = [1, 7, 14, 30]):
        """
        Calculate user retention for recent cohorts

        Args:
            cohort_days: List of day numbers to calculate retention for
        """
        try:
            async with AsyncSessionLocal() as db:
                # Get cohorts from last 30 days
                cutoff_date = datetime.utcnow() - timedelta(days=30)

                # Get all users grouped by registration date
                users_result = await db.execute(
                    select(
                        func.date_trunc('day', User.created_at).label('cohort_date'),
                        User.id
                    ).where(User.created_at >= cutoff_date)
                )
                users = users_result.all()

                # Group users by cohort
                cohorts = {}
                for cohort_date, user_id in users:
                    cohort_key = cohort_date.date()
                    if cohort_key not in cohorts:
                        cohorts[cohort_key] = []
                    cohorts[cohort_key].append(user_id)

                # Calculate retention for each cohort and day
                for cohort_date, user_ids in cohorts.items():
                    cohort_size = len(user_ids)

                    for day_num in cohort_days:
                        target_date = cohort_date + timedelta(days=day_num)
                        target_datetime = datetime.combine(target_date, datetime.min.time())

                        # Count how many users from this cohort were active on target day
                        retained_result = await db.execute(
                            select(func.count(func.distinct(UserEvent.user_id))).where(
                                UserEvent.user_id.in_(user_ids),
                                UserEvent.timestamp >= target_datetime,
                                UserEvent.timestamp < target_datetime + timedelta(days=1)
                            )
                        )
                        retained_users = retained_result.scalar()

                        retention_rate = (retained_users / cohort_size * 100) if cohort_size > 0 else 0

                        # Create or update retention record
                        cohort_datetime = datetime.combine(cohort_date, datetime.min.time())
                        result = await db.execute(
                            select(UserRetention).where(
                                UserRetention.cohort_date == cohort_datetime,
                                UserRetention.day_number == day_num
                            )
                        )
                        retention = result.scalars().first()

                        if not retention:
                            retention = UserRetention(
                                cohort_date=cohort_datetime,
                                day_number=day_num
                            )
                            db.add(retention)

                        retention.cohort_size = cohort_size
                        retention.retained_users = retained_users
                        retention.retention_rate = retention_rate

                await db.commit()
                logger.info(f"Updated retention stats for {len(cohorts)} cohorts")
        except Exception as e:
            logger.error(f"Failed to calculate retention: {e}", exc_info=True)


# Global analytics service instance
analytics = AnalyticsService()
