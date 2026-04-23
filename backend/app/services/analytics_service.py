from datetime import datetime, timedelta, timezone
from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.person import Person


class AnalyticsService:
    async def get_heatmap_data(self, db: AsyncSession) -> dict[str, object]:
        hourly_result = await db.execute(
            select(func.strftime("%H", Attendance.timestamp).label("hour"), func.count(Attendance.id)).group_by("hour")
        )
        daily_result = await db.execute(
            select(func.strftime("%w", Attendance.timestamp).label("weekday"), func.count(Attendance.id)).group_by("weekday")
        )

        today = datetime.now(timezone.utc).date()
        week_start = datetime.combine(today - timedelta(days=6), datetime.min.time())
        month_start = datetime.combine(today - timedelta(days=28), datetime.min.time())

        week_result = await db.execute(
            select(func.date(Attendance.timestamp).label("day"), func.count(Attendance.id))
            .where(Attendance.timestamp >= week_start)
            .group_by("day")
            .order_by("day")
        )

        month_result = await db.execute(
            select(func.strftime("%Y-%W", Attendance.timestamp).label("week"), func.count(Attendance.id))
            .where(Attendance.timestamp >= month_start)
            .group_by("week")
            .order_by("week")
        )

        weekday_map = {
            "0": "Sunday",
            "1": "Monday",
            "2": "Tuesday",
            "3": "Wednesday",
            "4": "Thursday",
            "5": "Friday",
            "6": "Saturday",
        }

        return {
            "hourly": {f"{int(hour):02d}:00": count for hour, count in hourly_result.all()},
            "daily": {weekday_map[str(day)]: count for day, count in daily_result.all()},
            "weekly_trend": [count for _, count in week_result.all()],
            "monthly_trend": [count for _, count in month_result.all()],
        }

    async def get_trends(self, db: AsyncSession) -> dict[str, object]:
        dept_result = await db.execute(
            select(Person.department, func.count(Attendance.id))
            .join(Attendance, Attendance.person_id == Person.id)
            .group_by(Person.department)
            .order_by(func.count(Attendance.id).desc())
        )

        confidence_result = await db.execute(
            select(
                func.round(Attendance.confidence_score, 1).label("bucket"),
                func.count(Attendance.id),
            )
            .group_by("bucket")
            .order_by("bucket")
        )

        top_result = await db.execute(
            select(Person.name, func.count(Attendance.id).label("count"))
            .join(Attendance, Attendance.person_id == Person.id)
            .group_by(Person.id)
            .order_by(func.count(Attendance.id).desc())
            .limit(5)
        )

        low_result = await db.execute(
            select(Person.name, func.count(Attendance.id).label("count"))
            .join(Attendance, Attendance.person_id == Person.id)
            .group_by(Person.id)
            .order_by(func.count(Attendance.id).asc())
            .limit(5)
        )

        avg_conf_result = await db.execute(select(func.avg(cast(Attendance.confidence_score, Float))))
        avg_conf = avg_conf_result.scalar() or 0.0

        return {
            "attendance_by_department": [{"department": d, "count": c} for d, c in dept_result.all()],
            "confidence_distribution": [{"bucket": float(b), "count": c} for b, c in confidence_result.all()],
            "most_frequent_attendees": [{"name": n, "count": c} for n, c in top_result.all()],
            "least_frequent_attendees": [{"name": n, "count": c} for n, c in low_result.all()],
            "average_confidence": float(avg_conf),
        }
