from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.attendance_service import AttendanceService


@pytest.mark.asyncio
async def test_mark_attendance_success() -> None:
    service = AttendanceService()
    db = AsyncMock()
    db.add = MagicMock()
    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    with patch("app.services.attendance_service.save_cropped_face", return_value="crop.jpg"):
        ok, message = await service.mark_attendance(db=db, person_id=1, confidence=0.95, cropped_face=frame)

    assert ok is True
    assert message == "Attendance marked"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_attendance_cooldown() -> None:
    service = AttendanceService()
    db = AsyncMock()
    db.add = MagicMock()
    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    service.last_marked[1] = datetime.now(timezone.utc) - timedelta(seconds=10)
    ok, message = await service.mark_attendance(db=db, person_id=1, confidence=0.95, cropped_face=frame)

    assert ok is False
    assert message == "Cooldown active"
    db.commit.assert_not_called()
