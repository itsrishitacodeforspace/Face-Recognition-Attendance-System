from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    department: str = Field(min_length=1, max_length=200)


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    department: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class PersonImageRead(BaseModel):
    id: int
    image_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class PersonRead(BaseModel):
    id: int
    name: str
    email: str
    department: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PersonDetail(PersonRead):
    image_count: int
    attendance_count: int
