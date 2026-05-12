from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import DATA_DIR, DB_PATH


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: Path = DB_PATH) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS draws (
                lottery_type TEXT NOT NULL,
                issue TEXT NOT NULL,
                draw_date TEXT NOT NULL,
                numbers_json TEXT NOT NULL,
                special_json TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (lottery_type, issue)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_draws_type_date ON draws(lottery_type, draw_date DESC)"
        )


@contextmanager
def connect(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_draws(lottery_type: str, draws: list[dict]) -> int:
    if not draws:
        return 0

    with connect() as conn:
        changed = 0
        for draw in draws:
            before = conn.total_changes
            conn.execute(
                """
                INSERT INTO draws (
                    lottery_type, issue, draw_date, numbers_json, special_json, source, fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lottery_type, issue) DO UPDATE SET
                    draw_date = excluded.draw_date,
                    numbers_json = excluded.numbers_json,
                    special_json = excluded.special_json,
                    source = excluded.source,
                    fetched_at = excluded.fetched_at
                """,
                (
                    lottery_type,
                    draw["issue"],
                    draw["draw_date"],
                    json.dumps(draw["numbers"], ensure_ascii=False),
                    json.dumps(draw.get("special", []), ensure_ascii=False),
                    draw.get("source", "unknown"),
                    utc_now_iso(),
                ),
            )
            if conn.total_changes > before:
                changed += 1
        return changed


def get_draws(lottery_type: str, limit: int = 200) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT lottery_type, issue, draw_date, numbers_json, special_json, source, fetched_at
            FROM draws
            WHERE lottery_type = ?
            ORDER BY draw_date DESC, issue DESC
            LIMIT ?
            """,
            (lottery_type, limit),
        ).fetchall()

    return [
        {
            "lottery_type": row["lottery_type"],
            "issue": row["issue"],
            "draw_date": row["draw_date"],
            "numbers": json.loads(row["numbers_json"]),
            "special": json.loads(row["special_json"]),
            "source": row["source"],
            "fetched_at": row["fetched_at"],
        }
        for row in rows
    ]

