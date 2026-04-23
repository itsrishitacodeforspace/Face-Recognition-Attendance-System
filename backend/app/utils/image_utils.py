import io
import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)


def load_image(path: str) -> np.ndarray | None:
    image = cv2.imread(path)
    if image is None:
        logger.warning("Unable to load image", extra={"path": path})
    return image


def bytes_to_cv2_image(payload: bytes) -> np.ndarray | None:
    try:
        image = Image.open(io.BytesIO(payload)).convert("RGB")
        np_image = np.array(image)
        return cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    except Exception as exc:
        logger.warning("Failed to parse uploaded image: %s", exc)
        return None


def crop_face(frame: np.ndarray, bbox: Any) -> np.ndarray:
    x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
    return frame[y1:y2, x1:x2]


def estimate_image_sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def face_bbox_area_ratio(image: np.ndarray, bbox: Any) -> float:
    try:
        x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
    except Exception:
        return 0.0

    image_h, image_w = image.shape[:2]
    if image_h <= 0 or image_w <= 0:
        return 0.0

    face_w = max(0, x2 - x1)
    face_h = max(0, y2 - y1)
    face_area = face_w * face_h
    image_area = image_w * image_h
    if image_area <= 0:
        return 0.0
    return float(face_area / image_area)
