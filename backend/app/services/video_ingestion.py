import asyncio
import logging
import os
from time import monotonic
from typing import Awaitable, Callable

import cv2
import numpy as np

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

FrameCallback = Callable[[np.ndarray], Awaitable[None]]


class VideoIngestionService:
    def __init__(self, source_type: str, source_path: str | None = None) -> None:
        self.source_type = source_type
        self.source_path = source_path
        self._running = False

    def _open_capture(self) -> cv2.VideoCapture:
        if self.source_type == "file":
            if not self.source_path:
                raise ValueError("source_path is required for file source")
            return cv2.VideoCapture(self.source_path)
        if self.source_type == "webcam":
            return cv2.VideoCapture(0 if not self.source_path else int(self.source_path))
        if self.source_type == "rtsp":
            if not self.source_path:
                raise ValueError("source_path is required for rtsp source")
            rtsp_source = self.source_path.strip()

            # Prefer TCP transport for RTSP to avoid UDP packet loss/firewall issues on Windows.
            previous_ffmpeg_options = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|stimeout;5000000|fflags;nobuffer|flags;low_delay|max_delay;500000"
            )
            try:
                capture = cv2.VideoCapture(rtsp_source, cv2.CAP_FFMPEG)
            finally:
                if previous_ffmpeg_options is None:
                    os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = previous_ffmpeg_options

            if capture.isOpened():
                # Keep only the latest frame to avoid multi-second lag in preview.
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return capture

            capture.release()
            capture = cv2.VideoCapture(rtsp_source)
            if capture.isOpened():
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return capture
        raise ValueError(f"Unsupported source_type: {self.source_type}")

    async def process_stream(self, frame_callback: FrameCallback) -> None:
        capture = self._open_capture()
        if not capture.isOpened():
            capture.release()
            if self.source_type == "webcam":
                raise RuntimeError(
                    "Unable to open webcam source on backend host. "
                    "Set webcam Source Path to a valid camera index (for example 0, 1) "
                    "or use Video File input."
                )
            if self.source_type == "rtsp":
                raise RuntimeError(
                    "Unable to open rtsp source. Verify URL format and connectivity from backend host: "
                    f"{self.source_path}"
                )
            raise RuntimeError(f"Unable to open {self.source_type} source: {self.source_path}")

        self._running = True
        process_interval = max(0.05, float(settings.frame_process_interval))
        read_failure_delay = min(process_interval, 0.1)
        last_processed_at = monotonic() - process_interval
        consecutive_failures = 0
        try:
            while self._running:
                ok, frame = capture.read()
                now = monotonic()
                if not ok or frame is None:
                    if self.source_type == "file":
                        break

                    consecutive_failures += 1
                    if self.source_type == "rtsp" and consecutive_failures >= 30:
                        capture.release()
                        capture = self._open_capture()
                        if not capture.isOpened():
                            raise RuntimeError(
                                "RTSP stream disconnected and reconnect attempt failed. "
                                "Check stream availability and credentials."
                            )
                        consecutive_failures = 0

                    await asyncio.sleep(read_failure_delay)
                    continue

                consecutive_failures = 0

                # RTSP streams should be drained continuously to avoid decoder artifacts.
                should_process = self.source_type == "file" or (now - last_processed_at) >= process_interval
                if should_process:
                    await frame_callback(frame)
                    last_processed_at = monotonic()

                if self.source_type == "rtsp":
                    # Drain a few queued packets so the next processed frame is closer to real-time.
                    for _ in range(2):
                        if not capture.grab():
                            break

                if self.source_type == "file":
                    await asyncio.sleep(process_interval)
                else:
                    await asyncio.sleep(0)
        except Exception as exc:
            logger.exception("Video processing failed: %s", exc)
            raise
        finally:
            capture.release()
            self._running = False

    def stop(self) -> None:
        self._running = False
