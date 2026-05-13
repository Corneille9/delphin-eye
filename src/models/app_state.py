from __future__ import annotations

from pathlib import Path
from typing import Callable

from models.entities import Detection, DetectionSource, ImageRecord, ImageStatus
from services.export_service import ExportService
from services.image_queue_service import ImageQueueService
from services.persistence_service import PersistenceService
from services.prediction_service import PredictionService


Listener = Callable[[], None]


class AppState:
    """Central observable state. Delegates IO to services and notifies UI."""

    LAST_FOLDER_KEY = 'last_folder'
    LAST_INDEX_KEY = 'last_index'

    def __init__(
        self,
        persistence: PersistenceService,
        queue: ImageQueueService,
        prediction: PredictionService,
        export: ExportService,
    ) -> None:
        self.persistence = persistence
        self.queue = queue
        self.prediction = prediction
        self.export = export

        self.current_index: int = 0
        self.selected_detection_index: int | None = None
        self.detection_progress: tuple[int, int] = (0, 0)
        self.export_running: bool = False
        self._listeners: list[Listener] = []

    # -- observer --------------------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def notify(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                pass

    # -- accessors -------------------------------------------------------

    @property
    def images(self) -> list[ImageRecord]:
        return self.queue.images

    @property
    def total(self) -> int:
        return len(self.queue.images)

    @property
    def current_image(self) -> ImageRecord | None:
        if not self.queue.images:
            return None
        self.current_index = max(0, min(self.current_index, len(self.queue.images) - 1))
        return self.queue.images[self.current_index]

    def counts(self) -> dict[ImageStatus, int]:
        result = {status: 0 for status in ImageStatus}
        for img in self.queue.images:
            result[img.status] = result.get(img.status, 0) + 1
        return result

    # -- folder / resume -------------------------------------------------

    def try_resume(self) -> bool:
        folder = self.persistence.get_state(self.LAST_FOLDER_KEY)
        if not folder:
            return False
        path = Path(folder)
        if not path.is_dir():
            return False
        self.load_folder(path)
        try:
            last_index = int(self.persistence.get_state(self.LAST_INDEX_KEY) or '0')
        except ValueError:
            last_index = 0
        if self.queue.images:
            self.current_index = max(0, min(last_index, len(self.queue.images) - 1))
        self.notify()
        return True

    def reset_folder(self) -> None:
        self.prediction.cancel()
        folder = self.queue.folder
        if folder is not None:
            self.persistence.clear_folder(folder)
        self.queue.clear()
        self.current_index = 0
        self.selected_detection_index = None
        self.detection_progress = (0, 0)
        self.persistence.set_state(self.LAST_FOLDER_KEY, '')
        self.persistence.set_state(self.LAST_INDEX_KEY, '0')
        self.notify()

    def load_folder(self, folder: Path) -> None:
        self.queue.load_folder(folder)
        self.current_index = 0
        self.selected_detection_index = None
        self.persistence.set_state(self.LAST_FOLDER_KEY, str(folder.resolve()))
        self.persistence.set_state(self.LAST_INDEX_KEY, '0')
        self.notify()

    # -- navigation ------------------------------------------------------

    def select_image(self, index: int) -> None:
        if not self.queue.images:
            return
        self.current_index = max(0, min(index, len(self.queue.images) - 1))
        self.selected_detection_index = None
        self.persistence.set_state(self.LAST_INDEX_KEY, str(self.current_index))
        self.notify()

    def next_image(self) -> None:
        self.select_image(self.current_index + 1)

    def previous_image(self) -> None:
        self.select_image(self.current_index - 1)

    # -- detections ------------------------------------------------------

    def select_detection(self, index: int | None) -> None:
        image = self.current_image
        if image is None:
            return
        if index is None:
            self.selected_detection_index = None
        elif 0 <= index < len(image.detections):
            self.selected_detection_index = index
        self.notify()

    def update_detection_box(self, local_id: int, x1: float, y1: float, x2: float, y2: float) -> None:
        image = self.current_image
        if image is None:
            return
        for det in image.detections:
            if det.local_id == local_id:
                det.x1, det.y1, det.x2, det.y2 = float(x1), float(y1), float(x2), float(y2)
                break
        self._mark_manual(image)
        self.persistence.save_detections(image)
        self.persistence.update_status(image)
        self.notify()

    def delete_detection(self, local_id: int) -> None:
        image = self.current_image
        if image is None:
            return
        image.detections = [d for d in image.detections if d.local_id != local_id]
        self.selected_detection_index = None
        self._mark_manual(image)
        self.persistence.save_detections(image)
        self.persistence.update_status(image)
        self.notify()

    def add_manual_detection(self, x1: float, y1: float, x2: float, y2: float) -> Detection:
        image = self.current_image
        if image is None:
            raise RuntimeError('Aucune image sélectionnée.')
        next_id = max((d.local_id for d in image.detections), default=0) + 1
        det = Detection(
            local_id=next_id,
            x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
            confidence=1.0,
            source=DetectionSource.MANUAL,
        )
        image.detections.append(det)
        self._mark_manual(image)
        self.persistence.save_detections(image)
        self.persistence.update_status(image)
        self.selected_detection_index = len(image.detections) - 1
        self.notify()
        return det

    def _mark_manual(self, image: ImageRecord) -> None:
        image.status = ImageStatus.MODIFIED

    def update_notes(self, text: str) -> None:
        image = self.current_image
        if image is None:
            return
        image.notes = text or ''
        self.persistence.update_notes(image)

    # -- detection run ---------------------------------------------------

    def run_detection(
        self,
        on_update: Callable[[], None],
        on_finished: Callable[[int], None],
        only_pending: bool = True,
    ) -> None:
        import asyncio
        loop = asyncio.get_event_loop()

        images = list(self.queue.images)
        total = sum(1 for i in images if not only_pending or i.status == ImageStatus.PENDING)
        self.detection_progress = (0, total)
        self.notify()

        def progress(done: int, total_: int, _img: ImageRecord) -> None:
            self.detection_progress = (done, total_)
            loop.call_soon_threadsafe(on_update)

        def done(processed: int) -> None:
            def _finish() -> None:
                self.queue.refresh()
                on_finished(processed)
            loop.call_soon_threadsafe(_finish)

        self.prediction.run_batch_async(images, progress, done, only_pending=only_pending)

    def cancel_detection(self) -> None:
        self.prediction.cancel()

    # -- export ----------------------------------------------------------

    def run_export_async(self, on_done: Callable[[dict], None]) -> None:
        import asyncio
        import threading
        loop = asyncio.get_event_loop()
        self.export_running = True
        self.notify()

        images = list(self.queue.images)

        def worker() -> None:
            try:
                result = self.export.export_all(images)
            except Exception as exc:
                result = {'error': str(exc)}
            finally:
                self.export_running = False

            def _finish() -> None:
                self.notify()
                on_done(result)

            loop.call_soon_threadsafe(_finish)

        threading.Thread(target=worker, daemon=True).start()
