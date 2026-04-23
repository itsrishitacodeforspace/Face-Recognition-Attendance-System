import json
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.models.person import Person
from app.models.person import PersonImage
from app.services.face_recognition import FaceRecognitionService


@pytest.mark.asyncio
async def test_get_person_embedding_averages_and_normalizes() -> None:
    service = FaceRecognitionService()
    db = AsyncMock()

    e1 = np.ones((512,), dtype=np.float32)
    e2 = np.full((512,), 2.0, dtype=np.float32)
    rows = [
        PersonImage(person_id=1, image_path="a.jpg", encoding_blob=json.dumps(e1.tolist())),
        PersonImage(person_id=1, image_path="b.jpg", encoding_blob=json.dumps(e2.tolist())),
    ]

    result_proxy = MagicMock()
    result_proxy.scalars.return_value.all.return_value = rows
    db.execute.return_value = result_proxy

    emb = await service.get_person_embedding(person_id=1, db=db)

    assert emb is not None
    assert emb.shape == (512,)
    assert np.isclose(np.linalg.norm(emb), 1.0)


def test_recognize_face_threshold() -> None:
    service = FaceRecognitionService()
    service._faiss = None
    service._index = object()
    service._index_to_person_id = [1]
    service._person_name_cache = {1: "Alice"}
    service._embeddings_cache = {1: np.ones((512,), dtype=np.float32).tolist()}

    def fake_extract(_):
        return np.ones((512,), dtype=np.float32), MagicMock(bbox=[0, 0, 10, 10])

    service.extract_embedding = fake_extract
    person_id, name, confidence, _ = service.recognize_face(np.zeros((16, 16, 3), dtype=np.uint8))

    assert person_id == 1
    assert name == "Alice"
    assert confidence > 0.6


def test_extract_embedding_uses_resize_fallback() -> None:
    service = FaceRecognitionService()
    image = np.zeros((24, 24, 3), dtype=np.uint8)
    embedding = np.ones((512,), dtype=np.float32)
    face = MagicMock(bbox=[0, 0, 10, 10], embedding=embedding)

    class FakeFaceApp:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, _img):
            self.calls += 1
            if self.calls == 1:
                return []
            return [face]

    service._face_app = FakeFaceApp()

    emb, detected_face = service.extract_embedding(image)

    assert emb is not None
    assert detected_face is face
    assert np.isclose(np.linalg.norm(emb), 1.0)


@pytest.mark.asyncio
async def test_training_quality_summary_flags_weak_profiles() -> None:
    service = FaceRecognitionService()
    db = AsyncMock()

    person = Person(id=1, name="Alice", email="alice@example.com", department="IT", is_active=True)
    good_embedding = np.ones((512,), dtype=np.float32)
    bad_embedding = np.concatenate([np.ones((256,), dtype=np.float32), -np.ones((256,), dtype=np.float32)]).astype(
        np.float32
    )
    rows = [
        PersonImage(person_id=1, image_path="a.jpg", encoding_blob=json.dumps(good_embedding.tolist())),
        PersonImage(person_id=1, image_path="b.jpg", encoding_blob=json.dumps(bad_embedding.tolist())),
    ]

    persons_proxy = MagicMock()
    persons_proxy.scalars.return_value.all.return_value = [person]
    images_proxy = MagicMock()
    images_proxy.scalars.return_value.all.return_value = rows
    db.execute.side_effect = [persons_proxy, images_proxy]

    summary = await service.get_training_quality_summary(db)

    assert summary["total_persons"] == 1
    assert summary["ready_persons"] == 0
    assert summary["weak_persons"] == 1
    assert summary["persons"][0]["name"] == "Alice"
    assert summary["persons"][0]["ready_for_high_confidence"] is False
    assert summary["persons"][0]["recommendation"].startswith("Add at least")
