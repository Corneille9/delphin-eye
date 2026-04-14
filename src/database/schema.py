from __future__ import annotations

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folder TEXT NOT NULL,
        filename TEXT NOT NULL,
        absolute_path TEXT NOT NULL UNIQUE,
        width INTEGER,
        height INTEGER,
        status TEXT NOT NULL DEFAULT 'pending',
        notes TEXT NOT NULL DEFAULT '',
        order_index INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_images_folder ON images(folder)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_images_status ON images(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id INTEGER NOT NULL,
        local_id INTEGER NOT NULL,
        x1 REAL NOT NULL,
        y1 REAL NOT NULL,
        x2 REAL NOT NULL,
        y2 REAL NOT NULL,
        confidence REAL NOT NULL DEFAULT 1.0,
        source TEXT NOT NULL DEFAULT 'auto',
        label TEXT NOT NULL DEFAULT 'dorsal_fin',
        FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_detections_image ON detections(image_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
)
