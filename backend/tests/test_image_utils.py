import numpy as np

from app.utils.image_utils import estimate_image_sharpness, face_bbox_area_ratio


def test_estimate_image_sharpness_higher_for_detailed_image() -> None:
    smooth = np.full((128, 128, 3), 127, dtype=np.uint8)
    detailed = np.zeros((128, 128, 3), dtype=np.uint8)
    detailed[::2, ::2] = 255

    smooth_score = estimate_image_sharpness(smooth)
    detailed_score = estimate_image_sharpness(detailed)

    assert detailed_score > smooth_score


def test_face_bbox_area_ratio() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    ratio = face_bbox_area_ratio(image, [10, 10, 30, 30])

    assert np.isclose(ratio, 0.04)