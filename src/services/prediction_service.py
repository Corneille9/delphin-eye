from __future__ import annotations

import threading
from typing import Callable

from config import get_settings
from models.entities import Detection, DetectionSource, ImageRecord, ImageStatus
from services.persistence_service import PersistenceService

ProgressCallback = Callable[[int, int, ImageRecord], None]
DoneCallback = Callable[[int], None]


class PredictionService:
    """Wraps Ultralytics YOLO inference with lazy loading and background run."""

    def __init__(self, persistence: PersistenceService) -> None:
        self._persistence = persistence
        self._settings = get_settings()
        self._model = None
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def model_available(self) -> bool:
        return self._settings.model_path.exists()

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            if not self.model_available():
                raise FileNotFoundError(
                    f"Modèle YOLO introuvable : {self._settings.model_path}"
                )
            from ultralytics import YOLO  # lazy import
            self._model = YOLO(str(self._settings.model_path))
        return self._model

    def predict_one(self, image: ImageRecord) -> list[Detection]:
        model = self._ensure_model()
        results = model.predict(
            source=str(image.absolute_path),
            imgsz=self._settings.inference_imgsz,
            conf=self._settings.inference_conf,
            verbose=False,
        )
        detections: list[Detection] = []
        if not results:
            return detections
        r = results[0]
        if r.boxes is None:
            return detections
        h, w = r.orig_shape if hasattr(r, 'orig_shape') else (image.height or 0, image.width or 0)
        if image.width is None or image.height is None:
            if w and h:
                image.width, image.height = int(w), int(h)
                self._persistence.update_dimensions(image)
        xyxy = r.boxes.xyxy.cpu().numpy() if hasattr(r.boxes, 'xyxy') else []
        confs = r.boxes.conf.cpu().numpy() if hasattr(r.boxes, 'conf') else []
        for idx, (box, conf) in enumerate(zip(xyxy, confs), start=1):
            x1, y1, x2, y2 = [float(v) for v in box]
            detections.append(
                Detection(
                    local_id=idx,
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=float(conf),
                    source=DetectionSource.AUTO,
                )
            )
        return detections

    def run_batch_async(
        self,
        images: list[ImageRecord],
        on_progress: ProgressCallback,
        on_done: DoneCallback,
        only_pending: bool = True,
    ) -> None:
        if self._running:
            return
        self._cancel.clear()
        self._running = True

        def worker() -> None:
            processed = 0
            targets = [img for img in images if not only_pending or img.status in (ImageStatus.PENDING, ImageStatus.DETECTED)]
            total = len(targets)
            try:
                for img in targets:
                    if self._cancel.is_set():
                        break
                    try:
                        dets = self.predict_one(img)
                    except Exception:
                        dets = []
                    img.detections = dets
                    img.status = ImageStatus.DETECTED
                    self._persistence.save_detections(img)
                    self._persistence.update_status(img)
                    processed += 1
                    try:
                        on_progress(processed, total, img)
                    except Exception:
                        pass
            finally:
                self._running = False
                try:
                    on_done(processed)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def cancel(self) -> None:
        self._cancel.set()
