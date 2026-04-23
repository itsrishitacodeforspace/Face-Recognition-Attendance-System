import base64
import binascii
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.api.deps import authenticate_access_token
from app.config import get_settings
from app.database import SessionLocal
from app.services.video_ingestion import VideoIngestionService
from app.utils.file_storage import VIDEO_UPLOADS_ROOT
from app.utils.image_utils import crop_face


logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def _decode_data_url_image(data_url: str) -> np.ndarray | None:
    try:
        if "," in data_url:
            _, encoded = data_url.split(",", 1)
        else:
            encoded = data_url
        raw = base64.b64decode(encoded)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except (ValueError, binascii.Error):
        return None


def _encode_preview_data_url(frame: np.ndarray) -> str | None:
    try:
        preview = frame
        frame_width = int(frame.shape[1])
        frame_height = int(frame.shape[0])

        # Keep preview payloads bounded while preserving aspect ratio for box overlays.
        max_preview_width = max(320, int(settings.preview_max_width))
        if frame_width > max_preview_width:
            scale = max_preview_width / float(frame_width)
            resized_height = max(1, int(round(frame_height * scale)))
            preview = cv2.resize(frame, (max_preview_width, resized_height), interpolation=cv2.INTER_AREA)

        jpeg_quality = max(40, min(100, int(settings.preview_jpeg_quality)))
        ok, encoded = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
        if not ok:
            return None

        encoded_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded_b64}"
    except Exception:
        return None


async def _process_frame(
    websocket: WebSocket,
    frame: np.ndarray,
    face_service,
    attendance_service,
    include_preview: bool = False,
) -> None:
    started = perf_counter()
    async with SessionLocal() as db:
        recognized_faces = face_service.recognize_faces(frame)
        faces_payload: list[dict[str, object]] = []
        any_match = False

        for item in recognized_faces:
            person_id = item.get("person_id")
            confidence = float(item.get("confidence") or 0.0)
            face = item.get("face")
            bbox = item.get("bbox")

            attendance_marked = False
            message = "No match"
            if person_id and face is not None:
                cropped = crop_face(frame, face.bbox)
                ok, mark_message = await attendance_service.mark_attendance(db, int(person_id), confidence, cropped)
                attendance_marked = ok
                message = mark_message
                any_match = True

            faces_payload.append(
                {
                    "person_id": person_id,
                    "name": item.get("name"),
                    "confidence": confidence,
                    "person_details": item.get("person_details"),
                    "meets_target": confidence >= settings.recognition_target_confidence,
                    "bbox": bbox,
                    "attendance_marked": attendance_marked,
                    "message": message,
                }
            )

        primary = faces_payload[0] if faces_payload else None
        payload = {
            "type": "recognition",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "person_id": primary.get("person_id") if primary else None,
            "name": primary.get("name") if primary else None,
            "person_details": primary.get("person_details") if primary else None,
            "confidence": float(primary.get("confidence") or 0.0) if primary else 0.0,
            "meets_target": bool(primary.get("meets_target")) if primary else False,
            "target_confidence": settings.recognition_target_confidence,
            "attendance_marked": bool(primary.get("attendance_marked")) if primary else False,
            "message": primary.get("message") if primary else "No match",
            "bbox": primary.get("bbox") if primary else None,
            "frame_width": int(frame.shape[1]),
            "frame_height": int(frame.shape[0]),
            "faces": faces_payload,
            "face_count": len(faces_payload),
            "any_match": any_match,
            "preview_image": _encode_preview_data_url(frame) if include_preview else None,
            "processing_ms": round((perf_counter() - started) * 1000, 2),
        }

        await websocket.send_text(json.dumps(payload))


@router.websocket("/ws/process")
async def process_stream_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return

    async with SessionLocal() as auth_db:
        try:
            await authenticate_access_token(token, auth_db)
        except Exception:
            await websocket.close(code=1008)
            return

    await websocket.accept()
    try:
        config = await websocket.receive_json()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected before config payload")
        return

    source_type = config.get("source_type", "webcam")
    source_path = config.get("source_path")
    if isinstance(source_path, str):
        source_path = source_path.strip() or None

    face_service = websocket.app.state.face_service
    attendance_service = websocket.app.state.attendance_service

    if source_type == "file" and source_path:
        resolved_source = Path(source_path).resolve()
        if not resolved_source.is_relative_to(VIDEO_UPLOADS_ROOT.resolve()):
            await websocket.send_json({"type": "error", "message": "Invalid source path"})
            await websocket.close(code=1008)
            return
        source_path = str(resolved_source)

    ingestion = VideoIngestionService(source_type=source_type, source_path=source_path)

    async def on_frame(frame) -> None:
        await _process_frame(
            websocket,
            frame,
            face_service,
            attendance_service,
            include_preview=True,
        )

    try:
        if source_type == "browser_webcam":
            while True:
                message = await websocket.receive_json()
                msg_type = message.get("type")
                if msg_type == "stop":
                    break
                if msg_type != "frame":
                    await websocket.send_json({"type": "error", "message": f"Unsupported message type: {msg_type}"})
                    continue

                raw_image = message.get("image", "")
                if isinstance(raw_image, str) and len(raw_image.encode("utf-8")) > settings.max_ws_frame_bytes:
                    await websocket.send_json({"type": "error", "message": "Frame payload too large"})
                    continue

                frame = _decode_data_url_image(raw_image)
                if frame is None:
                    await websocket.send_json({"type": "error", "message": "Invalid webcam frame payload"})
                    continue

                await _process_frame(
                    websocket,
                    frame,
                    face_service,
                    attendance_service,
                    include_preview=False,
                )
        else:
            await ingestion.process_stream(on_frame)

        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as exc:
        logger.exception("WebSocket processing failed: %s", exc)
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        ingestion.stop()
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
