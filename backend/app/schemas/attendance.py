from datetime import datetime
from pydantic import BaseModel


class AttendanceRead(BaseModel):
    id: int
    person_id: int
    person_name: str
    department: str
    timestamp: datetime
    confidence_score: float
    cropped_face_path: str


class AttendanceTodaySummary(BaseModel):
    total_today: int
    unique_today: int
    avg_confidence: float


class AttendanceUpdate(BaseModel):
    timestamp: datetime
    confidence_score: float
