import numpy as np

from app.config import get_settings
from app.websocket.stream_handler import _decode_data_url_image, _encode_preview_data_url


settings = get_settings()


def test_encode_preview_data_url_round_trips_frame() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[:, :, 1] = 255

    encoded = _encode_preview_data_url(frame)

    assert isinstance(encoded, str)
    assert encoded.startswith("data:image/jpeg;base64,")

    decoded = _decode_data_url_image(encoded)
    assert decoded is not None
    assert decoded.shape[0] == 120
    assert decoded.shape[1] == 160


def test_encode_preview_data_url_downscales_large_frames() -> None:
    frame = np.zeros((300, 2000, 3), dtype=np.uint8)

    encoded = _encode_preview_data_url(frame)

    assert isinstance(encoded, str)
    decoded = _decode_data_url_image(encoded)
    assert decoded is not None
    assert decoded.shape[1] <= settings.preview_max_width
