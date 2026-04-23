import json
import logging
from pathlib import Path
from time import perf_counter
from threading import RLock
from typing import Any

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.person import Person, PersonImage
from app.models.training_log import TrainingLog
from app.utils.cuda_utils import is_cuda_available
from app.utils.image_utils import load_image


logger = logging.getLogger(__name__)
settings = get_settings()


class FaceRecognitionService:
    def __init__(self) -> None:
        self._face_app: Any | None = None
        self._faiss: Any | None = None
        self._index: Any | None = None
        self._gpu_resources: Any | None = None
        self._torch: Any | None = None
        self._torch_embeddings: Any | None = None
        self._gpu_available: bool = False
        self._faiss_gpu_enabled: bool = False
        self._index_to_person_id: list[int] = []
        self._person_name_cache: dict[int, str] = {}
        self._person_details_cache: dict[int, dict[str, Any]] = {}
        self._embeddings_cache: dict[int, list[float]] = {}
        self._state_lock = RLock()
        self._model_dir = Path("data/models")
        self._model_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        self._gpu_available = bool(settings.cuda_enabled and is_cuda_available())
        if settings.gpu_strict_mode and not self._gpu_available:
            raise RuntimeError("GPU strict mode is enabled but CUDA is not available")

        try:
            import insightface

            ctx_id = 0 if self._gpu_available else -1
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if self._gpu_available else ["CPUExecutionProvider"]
            self._face_app = insightface.app.FaceAnalysis(name=settings.insightface_model, providers=providers)
            self._face_app.prepare(ctx_id=ctx_id, det_thresh=settings.face_detection_threshold)
            logger.info("InsightFace initialized", extra={"ctx_id": ctx_id})
        except Exception as exc:
            logger.exception("Failed to initialize InsightFace: %s", exc)
            self._face_app = None
            raise RuntimeError(
                "Face detection engine initialization failed. Ensure onnxruntime is installed "
                "and compatible with insightface."
            ) from exc

        try:
            import faiss

            self._faiss = faiss
            self._faiss_gpu_enabled = False
            self._index = faiss.IndexFlatIP(512)
            if self._gpu_available:
                try:
                    self._gpu_resources = faiss.StandardGpuResources()
                    self._index = faiss.index_cpu_to_gpu(self._gpu_resources, 0, self._index)
                    self._faiss_gpu_enabled = True
                    logger.info("FAISS GPU index initialized")
                except Exception as gpu_exc:
                    logger.warning("FAISS GPU unavailable: %s", gpu_exc)
            logger.info("FAISS index initialized")
        except Exception as exc:
            logger.exception("Failed to initialize FAISS: %s", exc)
            self._faiss = None
            self._index = None
            if settings.gpu_strict_mode and self._gpu_available:
                logger.warning("FAISS unavailable, GPU search will rely on Torch")

        if self._gpu_available:
            try:
                import torch

                self._torch = torch
            except Exception as exc:
                self._torch = None
                logger.warning("Torch import failed for GPU search: %s", exc)
                if settings.gpu_strict_mode:
                    raise RuntimeError("GPU strict mode requires torch with CUDA support") from exc

    def _normalize(self, emb: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(emb)
        if norm == 0:
            return emb
        return emb / norm

    def _detect_faces(self, image: np.ndarray) -> list[Any]:
        if self._face_app is None:
            logger.error("Face app not initialized")
            return []
        try:
            faces = self._face_app.get(image)
            return faces or []
        except Exception as exc:
            logger.warning("Face detection failed: %s", exc)
            return []

    def _resized_candidates(self, image: np.ndarray) -> list[np.ndarray]:
        # Retry with larger images to improve detection for small/distant faces.
        h, w = image.shape[:2]
        longest = max(h, w)
        candidates: list[np.ndarray] = []
        for scale in (1.5, 2.0):
            target_longest = int(longest * scale)
            if target_longest > 1920:
                continue
            resized = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            candidates.append(resized)
        return candidates

    def _extract_face(self, image: np.ndarray) -> Any | None:
        faces = self._detect_faces(image)
        if faces:
            return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        for candidate in self._resized_candidates(image):
            faces = self._detect_faces(candidate)
            if faces:
                logger.info("Face detected after resize fallback")
                return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        return None

    def _extract_faces(self, image: np.ndarray) -> list[Any]:
        faces = self._detect_faces(image)
        if not faces:
            return []
        # Sort left-to-right for stable rendering order.
        return sorted(faces, key=lambda f: float(f.bbox[0]))

    def extract_embedding(self, image: np.ndarray) -> tuple[np.ndarray | None, Any | None]:
        try:
            face = self._extract_face(image)
            if face is None:
                return None, None
            embedding = np.array(face.embedding, dtype=np.float32)
            return self._normalize(embedding), face
        except Exception as exc:
            logger.warning("Embedding extraction failed: %s", exc)
            return None, None

    def _embedding_from_face(self, face: Any) -> np.ndarray | None:
        try:
            embedding = np.array(face.embedding, dtype=np.float32)
            return self._normalize(embedding)
        except Exception as exc:
            logger.warning("Face embedding extraction failed: %s", exc)
            return None

    async def add_person_embeddings(self, person_id: int, image_paths: list[str], db: AsyncSession) -> tuple[int, int]:
        added = 0
        failed = 0
        for image_path in image_paths:
            try:
                image = load_image(image_path)
                if image is None:
                    failed += 1
                    continue
                embedding, _ = self.extract_embedding(image)
                if embedding is None:
                    failed += 1
                    continue

                result = await db.execute(
                    select(PersonImage).where(PersonImage.person_id == person_id, PersonImage.image_path == image_path)
                )
                person_image = result.scalar_one_or_none()
                if person_image is None:
                    person_image = PersonImage(person_id=person_id, image_path=image_path)
                    db.add(person_image)

                person_image.encoding_blob = json.dumps(embedding.tolist())
                added += 1
            except Exception as exc:
                logger.warning("Failed processing image", extra={"path": image_path, "error": str(exc)})
                failed += 1

        await db.commit()
        return added, failed

    async def get_person_embedding(self, person_id: int, db: AsyncSession) -> np.ndarray | None:
        result = await db.execute(select(PersonImage).where(PersonImage.person_id == person_id))
        rows = result.scalars().all()
        vectors: list[np.ndarray] = []
        for row in rows:
            if not row.encoding_blob:
                continue
            try:
                vec = np.array(json.loads(row.encoding_blob), dtype=np.float32)
                vectors.append(vec)
            except Exception as exc:
                logger.warning("Invalid encoding blob", extra={"person_id": person_id, "error": str(exc)})

        if not vectors:
            return None
        mean_vec = np.mean(np.stack(vectors), axis=0)
        return self._normalize(mean_vec.astype(np.float32))

    def _mean_pairwise_similarity(self, vectors: list[np.ndarray]) -> float | None:
        if len(vectors) < 2:
            return None

        normalized = np.stack([self._normalize(vec.astype(np.float32)) for vec in vectors]).astype(np.float32)
        sims = normalized @ normalized.T
        upper = sims[np.triu_indices(len(vectors), k=1)]
        if upper.size == 0:
            return None
        return float(np.mean(upper))

    async def get_training_quality_summary(self, db: AsyncSession) -> dict[str, Any]:
        min_images = settings.min_training_images_per_person
        target_confidence = settings.recognition_target_confidence

        result = await db.execute(select(Person).where(Person.is_active.is_(True)).order_by(Person.name.asc()))
        persons = result.scalars().all()

        items: list[dict[str, Any]] = []
        ready_persons = 0
        for person in persons:
            image_result = await db.execute(select(PersonImage).where(PersonImage.person_id == person.id))
            images = image_result.scalars().all()

            vectors: list[np.ndarray] = []
            missing_encodings = 0
            for row in images:
                if not row.encoding_blob:
                    missing_encodings += 1
                    continue
                try:
                    vectors.append(np.array(json.loads(row.encoding_blob), dtype=np.float32))
                except Exception:
                    missing_encodings += 1

            consistency = self._mean_pairwise_similarity(vectors)
            total_images = len(images)
            encoded_images = len(vectors)
            ready = (
                total_images >= min_images
                and encoded_images >= min_images
                and consistency is not None
                and consistency >= target_confidence
            )

            if total_images < min_images:
                recommendation = f"Add at least {min_images - total_images} more training images"
            elif encoded_images < min_images:
                recommendation = "Re-train to refresh missing or invalid encodings"
            elif consistency is None:
                recommendation = "Capture more varied but clear images to stabilize embeddings"
            elif consistency < target_confidence:
                recommendation = (
                    "Confidence is limited by image quality/variance; "
                    "re-capture with better lighting, face size, and frontal/angled poses"
                )
            else:
                recommendation = "Training quality looks strong"

            if ready:
                ready_persons += 1

            items.append(
                {
                    "person_id": person.id,
                    "name": person.name,
                    "total_images": total_images,
                    "encoded_images": encoded_images,
                    "missing_encodings": missing_encodings,
                    "embedding_consistency": consistency,
                    "ready_for_high_confidence": ready,
                    "recommendation": recommendation,
                }
            )

        return {
            "target_confidence": target_confidence,
            "min_images_per_person": min_images,
            "total_persons": len(items),
            "ready_persons": ready_persons,
            "weak_persons": len(items) - ready_persons,
            "persons": items,
        }

    def _build_faiss_index(self, vectors: np.ndarray) -> None:
        if self._faiss is None:
            return
        self._index = self._faiss.IndexFlatIP(512)
        self._faiss_gpu_enabled = False
        if self._gpu_available:
            try:
                self._gpu_resources = self._faiss.StandardGpuResources()
                self._index = self._faiss.index_cpu_to_gpu(self._gpu_resources, 0, self._index)
                self._faiss_gpu_enabled = True
            except Exception as exc:
                logger.warning("Failed to create FAISS GPU index: %s", exc)
        self._index.add(vectors)

    def _build_gpu_embedding_matrix(self, vectors: np.ndarray) -> None:
        self._torch_embeddings = None
        if not self._gpu_available:
            return
        if self._torch is None:
            if settings.gpu_strict_mode:
                raise RuntimeError("GPU strict mode requires torch CUDA tensor search")
            return
        try:
            self._torch_embeddings = self._torch.from_numpy(vectors).to("cuda")
        except Exception as exc:
            logger.warning("Failed to build GPU embedding matrix: %s", exc)
            if settings.gpu_strict_mode:
                raise

    def _search_with_torch_gpu(self, emb: np.ndarray) -> tuple[int | None, float]:
        if self._torch is None or self._torch_embeddings is None:
            return None, 0.0
        query = self._torch.from_numpy(emb.astype(np.float32)).to("cuda")
        sims = self._torch.matmul(self._torch_embeddings, query)
        best_score, best_idx = self._torch.max(sims, dim=0)
        idx = int(best_idx.item())
        score = float(best_score.item())
        if idx < 0 or idx >= len(self._index_to_person_id):
            return None, 0.0
        return self._index_to_person_id[idx], score

    def _search_embedding(self, emb: np.ndarray) -> tuple[int | None, str | None, float]:
        with self._state_lock:
            if self._gpu_available and self._torch_embeddings is not None:
                person_id, score = self._search_with_torch_gpu(emb)
                if person_id is None or score <= settings.recognition_threshold:
                    return None, None, score
                if score < settings.recognition_target_confidence:
                    logger.info(
                        "Low-confidence match detected",
                        extra={"person_id": person_id, "score": round(score, 4)},
                    )
                return person_id, self._person_name_cache.get(person_id), score

            if settings.gpu_strict_mode and self._gpu_available:
                logger.error("GPU strict mode blocked CPU similarity search fallback")
                return None, None, 0.0

            if self._faiss is None or self._index is None:
                best_person = None
                best_score = -1.0
                for person_id, vector in self._embeddings_cache.items():
                    candidate = np.array(vector, dtype=np.float32)
                    score = float(np.dot(emb, candidate))
                    if score > best_score:
                        best_person = person_id
                        best_score = score
                if best_person is None or best_score <= settings.recognition_threshold:
                    return None, None, 0.0
                if best_score < settings.recognition_target_confidence:
                    logger.info(
                        "Low-confidence match detected",
                        extra={"person_id": best_person, "score": round(best_score, 4)},
                    )
                return best_person, self._person_name_cache.get(best_person), best_score

            query = emb.reshape(1, -1).astype(np.float32)
            scores, indices = self._index.search(query, k=1)
            score = float(scores[0][0])
            idx = int(indices[0][0])
            if idx < 0 or idx >= len(self._index_to_person_id):
                return None, None, 0.0

            person_id = self._index_to_person_id[idx]
            if score <= settings.recognition_threshold:
                return None, None, score
            if score < settings.recognition_target_confidence:
                logger.info(
                    "Low-confidence match detected",
                    extra={"person_id": person_id, "score": round(score, 4)},
                )
            return person_id, self._person_name_cache.get(person_id), score

    async def rebuild_index(self, db: AsyncSession) -> dict[str, int]:
        start = perf_counter()
        total_images = 0
        failed_images = 0
        with self._state_lock:
            self._index_to_person_id = []
            self._person_name_cache = {}
            self._person_details_cache = {}
            self._embeddings_cache = {}

        result = await db.execute(select(Person).where(Person.is_active.is_(True)))
        persons = result.scalars().all()

        embeddings: list[np.ndarray] = []
        for person in persons:
            with self._state_lock:
                self._person_name_cache[person.id] = person.name
                self._person_details_cache[person.id] = {
                    "person_id": person.id,
                    "name": person.name,
                    "email": person.email,
                    "department": person.department,
                    "is_active": bool(person.is_active),
                }
            image_result = await db.execute(select(PersonImage).where(PersonImage.person_id == person.id))
            images = image_result.scalars().all()
            total_images += len(images)

            # Backfill missing encodings when possible.
            for img in images:
                if img.encoding_blob:
                    continue
                source = load_image(img.image_path)
                if source is None:
                    failed_images += 1
                    continue
                emb, _ = self.extract_embedding(source)
                if emb is None:
                    failed_images += 1
                    continue
                img.encoding_blob = json.dumps(emb.tolist())

            mean_emb = await self.get_person_embedding(person.id, db)
            if mean_emb is None:
                continue

            embeddings.append(mean_emb)
            with self._state_lock:
                self._index_to_person_id.append(person.id)
                self._embeddings_cache[person.id] = mean_emb.tolist()

        await db.commit()
        if embeddings:
            matrix = np.stack(embeddings).astype(np.float32)
            self._build_faiss_index(matrix)
            self._build_gpu_embedding_matrix(matrix)
        else:
            with self._state_lock:
                self._index = None
                self._torch_embeddings = None

        status = "success" if embeddings else "empty"
        db.add(
            TrainingLog(
                total_persons=len(self._index_to_person_id),
                total_images=total_images,
                status=status,
            )
        )
        await db.commit()

        duration_ms = int((perf_counter() - start) * 1000)
        self._save_cache_to_disk()
        self._save_index_to_disk()
        return {
            "total_persons": len(self._index_to_person_id),
            "total_images": total_images,
            "failed_images": failed_images,
            "duration_ms": duration_ms,
        }

    def recognize_face(self, face_image: np.ndarray) -> tuple[int | None, str | None, float, Any | None]:
        with self._state_lock:
            has_index = bool(self._index_to_person_id)
        if not has_index:
            return None, None, 0.0, None

        emb, face = self.extract_embedding(face_image)
        if emb is None:
            return None, None, 0.0, None
        person_id, name, score = self._search_embedding(emb)
        if person_id is None:
            return None, None, score, face
        return person_id, name, score, face

    def recognize_faces(self, frame: np.ndarray) -> list[dict[str, Any]]:
        with self._state_lock:
            has_index = bool(self._index_to_person_id)
        if not has_index:
            return []

        faces = self._extract_faces(frame)
        results: list[dict[str, Any]] = []
        for face in faces:
            emb = self._embedding_from_face(face)
            if emb is None:
                continue
            person_id, name, confidence = self._search_embedding(emb)
            person_details = self._person_details_cache.get(person_id) if person_id else None
            results.append(
                {
                    "person_id": person_id,
                    "name": name,
                    "confidence": float(confidence),
                    "person_details": person_details,
                    "face": face,
                    "bbox": [int(v) for v in face.bbox],
                }
            )
        return results

    def _save_index_to_disk(self) -> None:
        if self._faiss is None or self._index is None:
            return
        try:
            index_path = self._model_dir / "faiss_index.bin"
            cpu_index = self._index
            if hasattr(self._faiss, "index_gpu_to_cpu"):
                try:
                    cpu_index = self._faiss.index_gpu_to_cpu(self._index)
                except Exception:
                    cpu_index = self._index
            self._faiss.write_index(cpu_index, str(index_path))
        except Exception as exc:
            logger.warning("Failed to save FAISS index: %s", exc)

    def _save_cache_to_disk(self) -> None:
        try:
            cache_path = self._model_dir / "embeddings_cache.json"
            with self._state_lock:
                payload = {
                    "index_to_person_id": self._index_to_person_id,
                    "embeddings_cache": self._embeddings_cache,
                    "person_name_cache": self._person_name_cache,
                    "person_details_cache": self._person_details_cache,
                }
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save embedding cache: %s", exc)

    def load_index_from_disk(self) -> None:
        cache_path = self._model_dir / "embeddings_cache.json"
        if not cache_path.exists():
            return

        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            with self._state_lock:
                self._index_to_person_id = [int(x) for x in payload.get("index_to_person_id", [])]
                self._embeddings_cache = {int(k): v for k, v in payload.get("embeddings_cache", {}).items()}
                self._person_name_cache = {int(k): v for k, v in payload.get("person_name_cache", {}).items()}
                details_payload = payload.get("person_details_cache", {})
                self._person_details_cache = {
                    int(k): {
                        "person_id": int(v.get("person_id", k)),
                        "name": v.get("name"),
                        "email": v.get("email"),
                        "department": v.get("department"),
                        "is_active": bool(v.get("is_active", True)),
                    }
                    for k, v in details_payload.items()
                    if isinstance(v, dict)
                }

            with self._state_lock:
                valid_person_ids = [person_id for person_id in self._index_to_person_id if person_id in self._embeddings_cache]
                self._index_to_person_id = valid_person_ids
                vectors = [np.array(self._embeddings_cache[person_id], dtype=np.float32) for person_id in self._index_to_person_id]
            if vectors:
                matrix = np.stack(vectors).astype(np.float32)
                self._build_faiss_index(matrix)
                self._build_gpu_embedding_matrix(matrix)
        except Exception as exc:
            logger.warning("Failed to load embedding cache: %s", exc)
