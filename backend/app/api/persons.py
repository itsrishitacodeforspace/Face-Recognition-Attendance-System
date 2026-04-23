import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi import Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database import get_db
from app.models.attendance import Attendance
from app.models.person import Person, PersonImage
from app.schemas.person import PersonCreate, PersonDetail, PersonImageRead, PersonRead, PersonUpdate
from app.utils.file_storage import PERSON_IMAGES_ROOT, save_person_image
from app.utils.image_utils import bytes_to_cv2_image, estimate_image_sharpness, face_bbox_area_ratio
from app.config import get_settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["persons"])
settings = get_settings()


def _is_supported_image_bytes(payload: bytes) -> bool:
    # JPEG
    if len(payload) >= 3 and payload[:3] == b"\xff\xd8\xff":
        return True
    # PNG
    if len(payload) >= 8 and payload[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    return False


@router.post("/persons", response_model=PersonRead)
async def create_person(
    payload: PersonCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> PersonRead:
    person = Person(name=payload.name, email=payload.email, department=payload.department)
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return PersonRead.model_validate(person)


@router.get("/persons", response_model=list[PersonRead])
async def list_persons(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str = Query(default=""),
    include_inactive: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> list[PersonRead]:
    query = select(Person)
    if not include_inactive:
        query = query.where(Person.is_active.is_(True))
    if search:
        like = f"%{search}%"
        query = query.where((Person.name.ilike(like)) | (Person.email.ilike(like)))

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size).order_by(Person.id.desc()))
    rows = result.scalars().all()
    return [PersonRead.model_validate(row) for row in rows]


@router.get("/persons/{person_id}", response_model=PersonDetail)
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> PersonDetail:
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    image_count_result = await db.execute(select(func.count(PersonImage.id)).where(PersonImage.person_id == person_id))
    attendance_count_result = await db.execute(select(func.count(Attendance.id)).where(Attendance.person_id == person_id))

    return PersonDetail(
        id=person.id,
        name=person.name,
        email=person.email,
        department=person.department,
        is_active=person.is_active,
        created_at=person.created_at,
        image_count=int(image_count_result.scalar() or 0),
        attendance_count=int(attendance_count_result.scalar() or 0),
    )


@router.put("/persons/{person_id}", response_model=PersonRead)
async def update_person(
    person_id: int,
    payload: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> PersonRead:
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(person, key, value)

    await db.commit()
    await db.refresh(person)
    return PersonRead.model_validate(person)


@router.delete("/persons/{person_id}")
async def delete_person(
    person_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> dict[str, str]:
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    # Delete all images associated with this person
    images_result = await db.execute(select(PersonImage).where(PersonImage.person_id == person_id))
    images = images_result.scalars().all()
    for image in images:
        await db.delete(image)

    # Delete the person record
    await db.delete(person)
    await db.commit()

    # Rebuild face recognition index to remove deleted person's embeddings
    try:
        await request.app.state.face_service.rebuild_index(db)
    except Exception as exc:
        logger.warning("Retraining after person deletion failed: %s", exc)

    return {"message": "Person and all associated images deleted"}


@router.post("/persons/{person_id}/images")
async def upload_person_images(
    person_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> dict[str, object]:
    person_result = await db.execute(select(Person).where(Person.id == person_id, Person.is_active.is_(True)))
    person = person_result.scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    face_service = request.app.state.face_service

    results: list[dict[str, object]] = []

    # FastAPI injects state on app instance; retrieve via db bind context fallback isn't practical here.
    # Use global app state through router dependency in runtime.
    for upload in files:
        try:
            if upload.content_type not in {"image/jpeg", "image/png"}:
                results.append({"filename": upload.filename, "status": "failed", "reason": "Invalid file type"})
                continue

            payload = await upload.read(settings.max_image_upload_bytes + 1)
            if len(payload) > settings.max_image_upload_bytes:
                results.append({"filename": upload.filename, "status": "failed", "reason": "Image too large"})
                continue
            if not _is_supported_image_bytes(payload):
                results.append({"filename": upload.filename, "status": "failed", "reason": "Invalid image content"})
                continue

            image = bytes_to_cv2_image(payload)
            if image is None:
                results.append({"filename": upload.filename, "status": "failed", "reason": "Unreadable image"})
                continue

            path = save_person_image(person_id, upload.filename or "image.jpg", payload)
            db_image = PersonImage(person_id=person_id, image_path=path)
            db.add(db_image)
            await db.flush()

            if face_service is not None:
                embedding, face = face_service.extract_embedding(image)
                if embedding is None:
                    results.append({"filename": upload.filename, "status": "failed", "reason": "No face detected"})
                    await db.delete(db_image)
                    continue

                sharpness = estimate_image_sharpness(image)
                if sharpness < settings.min_training_image_sharpness:
                    results.append(
                        {
                            "filename": upload.filename,
                            "status": "failed",
                            "reason": (
                                "Image too blurry for training "
                                f"(sharpness {sharpness:.1f} < {settings.min_training_image_sharpness:.1f})"
                            ),
                        }
                    )
                    await db.delete(db_image)
                    continue

                if face is not None:
                    area_ratio = face_bbox_area_ratio(image, face.bbox)
                    if area_ratio < settings.min_training_face_area_ratio:
                        results.append(
                            {
                                "filename": upload.filename,
                                "status": "failed",
                                "reason": (
                                    "Face too small in frame for reliable training "
                                    f"(ratio {area_ratio:.3f} < {settings.min_training_face_area_ratio:.3f})"
                                ),
                            }
                        )
                        await db.delete(db_image)
                        continue

                db_image.encoding_blob = json.dumps(embedding.tolist())

            results.append({"filename": upload.filename, "status": "ok", "image_id": db_image.id})
        except Exception as exc:
            logger.warning("Image upload failed", extra={"file": upload.filename, "error": str(exc)})
            results.append({"filename": upload.filename, "status": "failed", "reason": str(exc)})

    await db.commit()

    # Optional auto-training.
    try:
        from app.config import get_settings

        if get_settings().auto_train_on_upload:
            await request.app.state.face_service.rebuild_index(db)
    except Exception as exc:
        logger.warning("Auto-training skipped: %s", exc)

    return {"person_id": person_id, "results": results}


@router.get("/persons/{person_id}/images", response_model=list[PersonImageRead])
async def list_person_images(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> list[PersonImageRead]:
    result = await db.execute(select(PersonImage).where(PersonImage.person_id == person_id).order_by(PersonImage.id.desc()))
    images = result.scalars().all()
    return [PersonImageRead.model_validate(image) for image in images]


@router.get("/images/{image_id}/preview")
async def preview_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> FileResponse:
    result = await db.execute(select(PersonImage).where(PersonImage.id == image_id))
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    path = Path(image.image_path)
    allowed_root = PERSON_IMAGES_ROOT.resolve()
    try:
        resolved_path = path.resolve()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image path")

    if not resolved_path.is_relative_to(allowed_root):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Image path outside allowed directory")

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found on disk")

    suffix = resolved_path.suffix.lower()
    media_type = "image/jpeg"
    if suffix == ".png":
        media_type = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"

    return FileResponse(path=str(resolved_path), media_type=media_type)


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> dict[str, str]:
    result = await db.execute(select(PersonImage).where(PersonImage.id == image_id))
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    await db.delete(image)
    await db.commit()

    try:
        await request.app.state.face_service.rebuild_index(db)
    except Exception as exc:
        logger.warning("Retraining after delete failed: %s", exc)

    return {"message": "Image deleted"}
