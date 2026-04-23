from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database import get_db
from app.models.training_log import TrainingLog
from app.schemas.training import (
    TrainingLogRead,
    TrainingLogUpdate,
    TrainingQualitySummary,
    TrainingSummary,
)
from fastapi import HTTPException, status


router = APIRouter(prefix="/api/train", tags=["training"])


@router.post("", response_model=TrainingSummary)
async def trigger_training(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> TrainingSummary:
    summary = await request.app.state.face_service.rebuild_index(db)
    return TrainingSummary(**summary, status="success")


@router.get("/status", response_model=TrainingLogRead | None)
async def get_training_status(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> TrainingLogRead | None:
    result = await db.execute(select(TrainingLog).order_by(TrainingLog.timestamp.desc()).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return TrainingLogRead.model_validate(row)


@router.get("/quality", response_model=TrainingQualitySummary)
async def get_training_quality(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> TrainingQualitySummary:
    summary = await request.app.state.face_service.get_training_quality_summary(db)
    return TrainingQualitySummary(**summary)


@router.get("/logs", response_model=list[TrainingLogRead])
async def list_training_logs(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> list[TrainingLogRead]:
    result = await db.execute(select(TrainingLog).order_by(TrainingLog.timestamp.desc()).limit(100))
    rows = result.scalars().all()
    return [TrainingLogRead.model_validate(row) for row in rows]


@router.get("/logs/{log_id}", response_model=TrainingLogRead)
async def get_training_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> TrainingLogRead:
    result = await db.execute(select(TrainingLog).where(TrainingLog.id == log_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training log not found")
    return TrainingLogRead.model_validate(row)


@router.put("/logs/{log_id}", response_model=TrainingLogRead)
async def update_training_log(
    log_id: int,
    payload: TrainingLogUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> TrainingLogRead:
    result = await db.execute(select(TrainingLog).where(TrainingLog.id == log_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training log not found")

    row.status = payload.status.strip() if payload.status else row.status
    await db.commit()
    await db.refresh(row)
    return TrainingLogRead.model_validate(row)
