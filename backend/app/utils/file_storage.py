from datetime import datetime, timezone
from pathlib import Path
import logging
import re
import secrets

import cv2
import numpy as np


logger = logging.getLogger(__name__)

DATA_ROOT = Path("data")
PERSON_IMAGES_ROOT = DATA_ROOT / "uploads" / "person_images"
ATTENDANCE_CROPS_ROOT = DATA_ROOT / "uploads" / "attendance_crops"
VIDEO_UPLOADS_ROOT = DATA_ROOT / "uploads" / "videos"
MODEL_ROOT = DATA_ROOT / "models"


def _safe_filename(filename: str, fallback_ext: str = "") -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = name.strip("._")
    if not name:
        return f"upload_{secrets.token_hex(8)}{fallback_ext}"
    return name


def ensure_storage_dirs() -> None:
    for path in [PERSON_IMAGES_ROOT, ATTENDANCE_CROPS_ROOT, VIDEO_UPLOADS_ROOT, MODEL_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def save_person_image(person_id: int, filename: str, image_bytes: bytes) -> str:
    ensure_storage_dirs()
    person_dir = PERSON_IMAGES_ROOT / str(person_id)
    person_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(filename, fallback_ext=".jpg")
    ts = int(datetime.now(timezone.utc).timestamp())
    output_path = person_dir / f"{ts}_{safe_name}"
    resolved_person_dir = person_dir.resolve()
    resolved_output = output_path.resolve()
    if not resolved_output.is_relative_to(resolved_person_dir):
        raise ValueError("Invalid upload filename")

    output_path.write_bytes(image_bytes)
    return str(output_path)


def save_cropped_face(person_id: int, cropped_face: np.ndarray, timestamp: datetime) -> str:
    ensure_storage_dirs()
    day_dir = ATTENDANCE_CROPS_ROOT / str(timestamp.year) / f"{timestamp.month:02d}" / f"{timestamp.day:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    file_path = day_dir / f"{person_id}_{int(timestamp.timestamp())}.jpg"
    ok = cv2.imwrite(str(file_path), cropped_face)
    if not ok:
        raise RuntimeError("Failed to write cropped face image")
    logger.info("Saved cropped face", extra={"path": str(file_path), "person_id": person_id})
    return str(file_path)


def save_uploaded_video(filename: str, video_bytes: bytes) -> str:
    ensure_storage_dirs()
    safe_name = _safe_filename(filename, fallback_ext=".mp4")
    ts = int(datetime.now(timezone.utc).timestamp())
    output_path = VIDEO_UPLOADS_ROOT / f"{ts}_{safe_name}"

    resolved_video_root = VIDEO_UPLOADS_ROOT.resolve()
    resolved_output = output_path.resolve()
    if not resolved_output.is_relative_to(resolved_video_root):
        raise ValueError("Invalid upload filename")

    output_path.write_bytes(video_bytes)
    logger.info("Saved video upload", extra={"path": str(output_path)})
    return str(output_path)
