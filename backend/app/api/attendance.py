import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database import get_db
from app.models.attendance import Attendance
from app.models.person import Person
from app.schemas.attendance import AttendanceRead, AttendanceTodaySummary, AttendanceUpdate
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/api/attendance", tags=["attendance"])
analytics_service = AnalyticsService()


@router.get("", response_model=list[AttendanceRead])
async def list_attendance(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    person_id: int | None = Query(default=None),
    department: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> list[AttendanceRead]:
    query = (
        select(Attendance, Person.name, Person.department)
        .join(Person, Person.id == Attendance.person_id)
        .order_by(Attendance.timestamp.desc())
    )

    filters = []
    if date_from:
        filters.append(Attendance.timestamp >= date_from)
    if date_to:
        filters.append(Attendance.timestamp <= date_to)
    if person_id:
        filters.append(Attendance.person_id == person_id)
    if department:
        filters.append(Person.department == department)

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    rows = result.all()
    return [
        AttendanceRead(
            id=attendance.id,
            person_id=attendance.person_id,
            person_name=name,
            department=dept,
            timestamp=attendance.timestamp,
            confidence_score=attendance.confidence_score,
            cropped_face_path=attendance.cropped_face_path,
        )
        for attendance, name, dept in rows
    ]


@router.get("/today", response_model=AttendanceTodaySummary)
async def get_today_summary(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> AttendanceTodaySummary:
    now = datetime.now(timezone.utc)
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    total_result = await db.execute(select(func.count(Attendance.id)).where(Attendance.timestamp >= day_start))
    unique_result = await db.execute(
        select(func.count(func.distinct(Attendance.person_id))).where(Attendance.timestamp >= day_start)
    )
    avg_result = await db.execute(select(func.avg(Attendance.confidence_score)).where(Attendance.timestamp >= day_start))

    return AttendanceTodaySummary(
        total_today=int(total_result.scalar() or 0),
        unique_today=int(unique_result.scalar() or 0),
        avg_confidence=float(avg_result.scalar() or 0.0),
    )


@router.get("/export")
async def export_csv(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> StreamingResponse:
    query = select(Attendance, Person.name, Person.department).join(Person, Person.id == Attendance.person_id)
    if date_from:
        query = query.where(Attendance.timestamp >= date_from)
    if date_to:
        query = query.where(Attendance.timestamp <= date_to)

    result = await db.execute(query.order_by(Attendance.timestamp.desc()))
    rows = result.all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["attendance_id", "person_id", "name", "department", "timestamp", "confidence"])
    for attendance, name, dept in rows:
        writer.writerow(
            [attendance.id, attendance.person_id, name, dept, attendance.timestamp.isoformat(), attendance.confidence_score]
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"},
    )


@router.get("/heatmap")
async def get_heatmap(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> dict[str, object]:
    return await analytics_service.get_heatmap_data(db)


@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> dict[str, object]:
    return await analytics_service.get_trends(db)


@router.put("/{attendance_id}", response_model=AttendanceRead)
async def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> AttendanceRead:
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    attendance.timestamp = payload.timestamp
    attendance.confidence_score = payload.confidence_score
    await db.commit()
    await db.refresh(attendance)

    person_result = await db.execute(select(Person).where(Person.id == attendance.person_id))
    person = person_result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    return AttendanceRead(
        id=attendance.id,
        person_id=attendance.person_id,
        person_name=person.name,
        department=person.department,
        timestamp=attendance.timestamp,
        confidence_score=attendance.confidence_score,
        cropped_face_path=attendance.cropped_face_path,
    )


@router.delete("/{attendance_id}")
async def delete_attendance(
    attendance_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> dict[str, str]:
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()
    if attendance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    await db.delete(attendance)
    await db.commit()
    return {"message": "Attendance record deleted"}
