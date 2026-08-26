from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

from config import get_settings
from models.entities import Detection, DetectionSource, ImageRecord, ImageStatus
from services.persistence_service import PersistenceService

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Outcome of a detection run, as reported to the UI."""

    analysed: int = 0
    detections: int = 0
    failed: int = 0
    cancelled: bool = False
    error: str = ''


ProgressCallback = Callable[[int, int, ImageRecord], None]
DoneCallback = Callable[[BatchResult], None]


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
            if self._settings.inference_mode == 'sahi':
                from sahi import AutoDetectionModel
                self._model = AutoDetectionModel.from_pretrained(
                    model_type="ultralytics",
                    model_path=str(self._settings.model_path),
                    confidence_threshold=self._settings.inference_conf,
                    device="cpu",
                )
            else:
                from ultralytics import YOLO
                self._model = YOLO(str(self._settings.model_path))
        return self._model

    def predict_one(self, image: ImageRecord) -> list[Detection]:
        model = self._ensure_model()
        detections: list[Detection] = []

        if self._settings.inference_mode == 'sahi':
            from sahi.predict import get_sliced_prediction
            result = get_sliced_prediction(
                str(image.absolute_path),
                model,
                slice_height=self._settings.inference_imgsz,
                slice_width=self._settings.inference_imgsz,
                overlap_height_ratio=self._settings.inference_overlap,
                overlap_width_ratio=self._settings.inference_overlap,
            )
            if image.width is None or image.height is None:
                from PIL import Image as PILImage
                with PILImage.open(str(image.absolute_path)) as pil_img:
                    image.width, image.height = pil_img.size
                self._persistence.update_dimensions(image)
            for idx, pred in enumerate(result.object_prediction_list, start=1):
                x1, y1, x2, y2 = pred.bbox.to_xyxy()
                detections.append(
                    Detection(
                        local_id=idx,
                        x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
                        confidence=float(pred.score.value),
                        source=DetectionSource.AUTO,
                    )
                )
        else:
            results = model.predict(
                source=str(image.absolute_path),
                imgsz=self._settings.inference_imgsz,
                conf=self._settings.inference_conf,
                verbose=False,
            )
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
        targets: list[ImageRecord],
        on_progress: ProgressCallback,
        on_done: DoneCallback,
    ) -> None:
        """Analyse `targets` in a background thread. Never raises to the caller."""
        if self._running:
            return
        self._cancel.clear()
        self._running = True

        def worker() -> None:
            result = BatchResult()
            total = len(targets)
            try:
                # Load once up front: a broken model would otherwise fail on
                # every image in turn and report a whole run of failures
                # instead of the single reason behind them.
                self._ensure_model()
            except Exception as exc:
                result.error = self._describe(exc)
                logger.exception('Model could not be loaded')
                self._finish(result, on_done)
                return

            try:
                for done, img in enumerate(targets, start=1):
                    if self._cancel.is_set():
                        result.cancelled = True
                        break
                    try:
                        detections = self.predict_one(img)
                    except Exception as exc:
                        # The image keeps a status of its own: silently leaving
                        # it "analysed with no fin" is what made a whole broken
                        # run look like a successful one.
                        img.detections = []
                        img.status = ImageStatus.FAILED
                        result.failed += 1
                        if not result.error:
                            result.error = self._describe(exc)
                        logger.exception('Detection failed on %s', img.filename)
                    else:
                        img.detections = detections
                        img.status = (
                            ImageStatus.DETECTED if detections else ImageStatus.EMPTY
                        )
                        result.analysed += 1
                        result.detections += len(detections)

                    self._persistence.save_detections(img)
                    self._persistence.update_status(img)
                    try:
                        on_progress(done, total, img)
                    except Exception:
                        logger.exception('Progress callback failed')
            finally:
                self._finish(result, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, result: BatchResult, on_done: DoneCallback) -> None:
        self._running = False
        try:
            on_done(result)
        except Exception:
            logger.exception('Completion callback failed')

    @staticmethod
    def _describe(exc: Exception) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        return f'{type(exc).__name__} : {message}'

    def reset_model(self) -> None:
        with self._lock:
            self._model = None

    def cancel(self) -> None:
        self._cancel.set()