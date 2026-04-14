from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator

from config import get_settings
from database.schema import SCHEMA_STATEMENTS


class Repository:
    """Thin SQLite wrapper. All methods return plain rows/dicts."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = RLock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        return conn

    def _initialize(self) -> None:
        with self.transaction() as conn:
            for stmt in SCHEMA_STATEMENTS:
                conn.execute(stmt)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN')
                yield conn
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

    # -- images ----------------------------------------------------------

    def clear_folder(self, folder: str) -> None:
        with self.transaction() as conn:
            conn.execute('DELETE FROM images WHERE folder = ?', (folder,))

    def insert_images(self, folder: str, records: list[dict]) -> None:
        with self.transaction() as conn:
            for idx, rec in enumerate(records):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO images
                        (folder, filename, absolute_path, width, height, status, order_index)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        folder,
                        rec['filename'],
                        rec['absolute_path'],
                        rec.get('width'),
                        rec.get('height'),
                        idx,
                    ),
                )

    def list_images(self, folder: str) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            return list(
                conn.execute(
                    'SELECT * FROM images WHERE folder = ? ORDER BY order_index ASC',
                    (folder,),
                )
            )

    def update_image_status(self, image_id: int, status: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE images SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, image_id),
            )

    def update_image_notes(self, image_id: int, notes: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE images SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (notes, image_id),
            )

    def update_image_dimensions(self, image_id: int, width: int, height: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                'UPDATE images SET width = ?, height = ? WHERE id = ?',
                (width, height, image_id),
            )

    # -- detections ------------------------------------------------------

    def replace_detections(self, image_id: int, detections: list[dict]) -> None:
        with self.transaction() as conn:
            conn.execute('DELETE FROM detections WHERE image_id = ?', (image_id,))
            for det in detections:
                conn.execute(
                    """
                    INSERT INTO detections
                        (image_id, local_id, x1, y1, x2, y2, confidence, source, label)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        image_id,
                        det['local_id'],
                        det['x1'],
                        det['y1'],
                        det['x2'],
                        det['y2'],
                        det.get('confidence', 1.0),
                        det.get('source', 'auto'),
                        det.get('label', 'dorsal_fin'),
                    ),
                )

    def list_detections(self, image_id: int) -> list[sqlite3.Row]:
        with self.transaction() as conn:
            return list(
                conn.execute(
                    'SELECT * FROM detections WHERE image_id = ? ORDER BY local_id ASC',
                    (image_id,),
                )
            )

    # -- app_state -------------------------------------------------------

    def set_state(self, key: str, value: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO app_state(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_state(self, key: str, default: str | None = None) -> str | None:
        with self.transaction() as conn:
            row = conn.execute('SELECT value FROM app_state WHERE key = ?', (key,)).fetchone()
            return row['value'] if row else default


_REPO: Repository | None = None


def get_repository() -> Repository:
    global _REPO
    if _REPO is None:
        _REPO = Repository(get_settings().database_path)
    return _REPO
