from datetime import datetime, timedelta, timezone
import logging

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.attendance import Attendance
from app.utils.file_storage import save_cropped_face


logger = logging.getLogger(__name__)
settings = get_settings()


class AttendanceService:
    def __init__(self) -> None:
        self.last_marked: dict[int, datetime] = {}

    def _prune_last_marked(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=settings.attendance_cooldown_seconds * 2)
        stale_ids = [person_id for person_id, marked_at in self.last_marked.items() if marked_at < cutoff]
        for person_id in stale_ids:
            self.last_marked.pop(person_id, None)

    async def mark_attendance(
        self,
        db: AsyncSession,
        person_id: int,
        confidence: float,
        cropped_face: np.ndarray,
    ) -> tuple[bool, str]:
        now = datetime.now(timezone.utc)
        self._prune_last_marked(now)

        if confidence <= settings.recognition_threshold:
            return False, "Confidence too low"

        if person_id in self.last_marked:
            elapsed = (now - self.last_marked[person_id]).total_seconds()
            if elapsed < settings.attendance_cooldown_seconds:
                return False, "Cooldown active"

        try:
            face_path = save_cropped_face(person_id=person_id, cropped_face=cropped_face, timestamp=now)
            db.add(
                Attendance(
                    person_id=person_id,
                    timestamp=now,
                    confidence_score=confidence,
                    cropped_face_path=face_path,
                )
            )
            await db.commit()
            self.last_marked[person_id] = now
            logger.info("Attendance marked", extra={"person_id": person_id, "confidence": confidence})
            return True, "Attendance marked"
        except Exception as exc:
            await db.rollback()
            logger.exception("Failed to mark attendance: %s", exc)
            return False, "Failed to save attendance"
