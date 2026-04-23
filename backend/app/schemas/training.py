from datetime import datetime
from pydantic import BaseModel


class TrainingSummary(BaseModel):
    total_persons: int
    total_images: int
    failed_images: int
    duration_ms: int
    status: str


class TrainingQualityPerson(BaseModel):
    person_id: int
    name: str
    total_images: int
    encoded_images: int
    missing_encodings: int
    embedding_consistency: float | None
    ready_for_high_confidence: bool
    recommendation: str


class TrainingQualitySummary(BaseModel):
    target_confidence: float
    min_images_per_person: int
    total_persons: int
    ready_persons: int
    weak_persons: int
    persons: list[TrainingQualityPerson]


class TrainingLogRead(BaseModel):
    id: int
    timestamp: datetime
    total_persons: int
    total_images: int
    status: str

    class Config:
        from_attributes = True


class TrainingLogUpdate(BaseModel):
    status: str
