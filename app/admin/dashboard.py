"""
Admin dashboard for viewing bot analytics
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc
from typing import List, Dict, Any

from app.db.database import AsyncSessionLocal
from app.db.analytics_models import (
    DailyUserStats,
    FeatureUsageStats,
    SubscriptionStats,
    UserEvent,
    UserRetention
)
from app.db.models import User, Subscription

router = APIRouter()
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Main admin dashboard page"""

    try:
        async with AsyncSessionLocal() as db:
            # Get last 30 days of daily stats
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            daily_stats_result = await db.execute(
                select(DailyUserStats)
                .where(DailyUserStats.date >= thirty_days_ago)
                .order_by(DailyUserStats.date)
            )
            daily_stats = daily_stats_result.scalars().all()

            # Get today's stats
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_stats_result = await db.execute(
                select(DailyUserStats).where(DailyUserStats.date == today)
            )
            today_stats = today_stats_result.scalars().first()

            # Get total users count
            total_users_result = await db.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0

            # Get active subscriptions count
            active_subs_result = await db.execute(
                select(func.count(Subscription.id)).where(Subscription.is_active == True)
            )
            active_subscriptions = active_subs_result.scalar() or 0

            # Get feature usage stats for last 7 days
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            feature_stats_result = await db.execute(
                select(
                    FeatureUsageStats.feature_name,
                    func.sum(FeatureUsageStats.usage_count).label('total_usage'),
                    func.sum(FeatureUsageStats.unique_users).label('total_users')
                )
                .where(FeatureUsageStats.date >= seven_days_ago)
                .group_by(FeatureUsageStats.feature_name)
                .order_by(desc('total_usage'))
            )
            feature_stats = feature_stats_result.all()

            # Get recent events (last 100)
            recent_events_result = await db.execute(
                select(UserEvent)
                .order_by(desc(UserEvent.timestamp))
                .limit(100)
            )
            recent_events = recent_events_result.scalars().all()

            # Get subscription stats for last 30 days
            sub_stats_result = await db.execute(
                select(SubscriptionStats)
                .where(SubscriptionStats.date >= thirty_days_ago)
                .order_by(SubscriptionStats.date)
            )
            sub_stats = sub_stats_result.scalars().all()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "daily_stats": daily_stats,
            "today_stats": today_stats,
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "feature_stats": feature_stats,
            "recent_events": recent_events[:20],  # Show only 20 most recent
            "sub_stats": sub_stats
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error rendering admin dashboard: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{str(e)}</pre>",
            status_code=500
        )


@router.get("/admin/api/stats", response_model=Dict[str, Any])
async def get_stats_api():
    """API endpoint for getting stats (for charts)"""

    async with AsyncSessionLocal() as db:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Get daily stats
        daily_stats_result = await db.execute(
            select(DailyUserStats)
            .where(DailyUserStats.date >= thirty_days_ago)
            .order_by(DailyUserStats.date)
        )
        daily_stats = daily_stats_result.scalars().all()

        # Format for charts
        dates = [stat.date.strftime("%Y-%m-%d") for stat in daily_stats]
        active_users = [stat.active_users for stat in daily_stats]
        new_users = [stat.new_users for stat in daily_stats]
        total_messages = [stat.total_messages for stat in daily_stats]

        return {
            "dates": dates,
            "active_users": active_users,
            "new_users": new_users,
            "total_messages": total_messages
        }
