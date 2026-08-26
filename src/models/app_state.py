from __future__ import annotations

from pathlib import Path
from typing import Callable

from models.entities import (
    ANALYSED_STATUSES, Detection, DetectionSource, ImageRecord, ImageStatus,
)
from services.export_service import ExportService
from services.image_queue_service import ImageQueueService
from services.persistence_service import PersistenceService
from services.prediction_service import BatchResult, PredictionService

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
        self.queue_filter: str = 'all'
        self._listeners: list[Listener] = []


    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def notify(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                pass

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

    @property
    def triees_dir(self) -> Path | None:
        folder = self.queue.folder
        return self.export.compute_triees_path(Path(folder)) if folder else None

    @property
    def analysed_count(self) -> int:
        return sum(1 for img in self.queue.images if img.status in ANALYSED_STATUSES)

    def matches_filter(self, image: ImageRecord) -> bool:
        if self.queue_filter == 'all':
            return True
        if self.queue_filter == 'analysed':
            return image.status in ANALYSED_STATUSES
        return image.status.value == self.queue_filter

    def visible_indexes(self) -> list[int]:
        """Queue positions the sidebar is showing, in order."""
        return [
            index for index, img in enumerate(self.queue.images)
            if self.matches_filter(img)
        ]

    def set_queue_filter(self, value: str) -> None:
        if value == self.queue_filter:
            return
        self.queue_filter = value
        # Keep the current image on screen when it survives the new filter, so
        # the arrows carry on from where the user actually is.
        visible = self.visible_indexes()
        if visible and self.current_index not in visible:
            self.current_index = visible[0]
            self.selected_detection_index = None
            self.persistence.set_state(self.LAST_INDEX_KEY, str(self.current_index))
        self.notify()

    def detection_targets(self, force_all: bool = False) -> list[ImageRecord]:
        """Images the next run should analyse.

        Manual edits are never overwritten. Otherwise the run picks up what has
        not been analysed yet, and falls back to a full re-run once everything
        has - which is what the user means by pressing the button again.
        """
        if force_all:
            return [
                img for img in self.queue.images
                if img.status != ImageStatus.MODIFIED
            ]
        return [
            img for img in self.queue.images
            if img.status in (ImageStatus.PENDING, ImageStatus.FAILED)
        ]

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

    def select_image(self, index: int) -> None:
        if not self.queue.images:
            return
        self.current_index = max(0, min(index, len(self.queue.images) - 1))
        self.selected_detection_index = None
        self.persistence.set_state(self.LAST_INDEX_KEY, str(self.current_index))
        self.notify()

    def _step(self, offset: int) -> None:
        """Move within the filtered view, which is what the sidebar shows.

        Stepping over the raw queue instead would land on images the sidebar is
        hiding, and the highlighted row would stop following the canvas.
        """
        visible = self.visible_indexes()
        if not visible:
            return
        if self.current_index in visible:
            position = visible.index(self.current_index) + offset
        else:
            position = 0 if offset > 0 else len(visible) - 1
        position = max(0, min(position, len(visible) - 1))
        self.select_image(visible[position])

    def next_image(self) -> None:
        self._step(1)

    def previous_image(self) -> None:
        self._step(-1)

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

    def run_detection(
            self,
            on_update: Callable[[], None],
            on_finished: Callable[[BatchResult], None],
            force_all: bool = False,
    ) -> int:
        """Start a run and return how many images it will analyse."""
        import asyncio
        loop = asyncio.get_event_loop()

        targets = self.detection_targets(force_all=force_all)
        self.detection_progress = (0, len(targets))
        self.notify()

        def progress(done: int, total: int, _img: ImageRecord) -> None:
            self.detection_progress = (done, total)
            loop.call_soon_threadsafe(on_update)

        def done(result: BatchResult) -> None:
            def _finish() -> None:
                self.queue.refresh()
                on_finished(result)

            loop.call_soon_threadsafe(_finish)

        self.prediction.run_batch_async(targets, progress, done)
        return len(targets)

    def cancel_detection(self) -> None:
        self.prediction.cancel()

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
