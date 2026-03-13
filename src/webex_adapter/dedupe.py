"""Store SQLite para deduplicacion de eventos Webex.

Instrucciones:
- Usa SQLite para evitar duplicados entre reinicios del proceso.
- Deduplica por `message_id` y mantiene un estado `processing` / `processed` / `ignored`.
- Libera la marca si el procesamiento falla para permitir reintentos.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EventClaim:
    """Identidad minima del evento a deduplicar."""

    event_key: str
    message_id: str
    webhook_event_id: str
    room_id: str | None
    person_id: str | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


class WebexEventDedupeStore:
    """Deduplicacion simple basada en SQLite para el adaptador Webex."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_key TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    webhook_event_id TEXT NOT NULL,
                    room_id TEXT,
                    person_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_processed_events_updated_at ON processed_events(updated_at)"
            )

    def claim(
        self,
        claim: EventClaim,
        *,
        metadata: dict[str, Any] | None = None,
        stale_after_minutes: int = 10,
    ) -> bool:
        """Intenta reservar un evento para procesamiento.

        Retorna `True` si esta ejecucion obtuvo la reserva.
        Retorna `False` si el evento ya fue procesado o esta en curso.
        """
        now = _utc_now()
        stale_before = now - timedelta(minutes=stale_after_minutes)
        metadata_json = json.dumps(metadata or {}, ensure_ascii=True, sort_keys=True)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, updated_at FROM processed_events WHERE event_key = ?",
                (claim.event_key,),
            ).fetchone()

            if row is None:
                connection.execute(
                    """
                    INSERT INTO processed_events (
                        event_key, status, message_id, webhook_event_id, room_id,
                        person_id, created_at, updated_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claim.event_key,
                        "processing",
                        claim.message_id,
                        claim.webhook_event_id,
                        claim.room_id,
                        claim.person_id,
                        now.isoformat(),
                        now.isoformat(),
                        metadata_json,
                    ),
                )
                connection.commit()
                return True

            status = row["status"]
            updated_at = _parse_datetime(row["updated_at"])
            if status in {"processed", "ignored"}:
                connection.commit()
                return False
            if status == "processing" and updated_at and updated_at >= stale_before:
                connection.commit()
                return False

            connection.execute(
                """
                UPDATE processed_events
                SET status = ?, message_id = ?, webhook_event_id = ?, room_id = ?,
                    person_id = ?, updated_at = ?, metadata_json = ?
                WHERE event_key = ?
                """,
                (
                    "processing",
                    claim.message_id,
                    claim.webhook_event_id,
                    claim.room_id,
                    claim.person_id,
                    now.isoformat(),
                    metadata_json,
                    claim.event_key,
                ),
            )
            connection.commit()
            return True

    def mark_completed(
        self,
        event_key: str,
        *,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Marca un evento como `processed` o `ignored`."""
        if status not in {"processed", "ignored"}:
            raise ValueError("status invalido para mark_completed")

        now = _utc_now().isoformat()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=True, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "UPDATE processed_events SET status = ?, updated_at = ?, metadata_json = ? WHERE event_key = ?",
                (status, now, metadata_json, event_key),
            )
            connection.commit()

    def release_claim(self, event_key: str) -> None:
        """Libera una reserva fallida para que Webex pueda reintentar."""
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM processed_events WHERE event_key = ? AND status = ?",
                (event_key, "processing"),
            )
            connection.commit()

    def cleanup_expired(self, ttl_hours: int) -> int:
        """Elimina registros viejos para evitar crecimiento indefinido."""
        cutoff = (_utc_now() - timedelta(hours=ttl_hours)).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM processed_events WHERE updated_at < ?",
                (cutoff,),
            )
            connection.commit()
            return cursor.rowcount or 0
