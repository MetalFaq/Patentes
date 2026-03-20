"""Scheduler incremental para sincronizar SharePoint e indexar cambios.

Instrucciones:
- Opera solo cuando `PATENTES_SOURCE_MODE=sharepoint`.
- Usa polling por franja horaria; no depende de webhooks ni triggers externos.
- Cada corrida consulta Graph, descarga solo PDFs nuevos/modificados y reindexa
  solo lo necesario.
- Evita solapamientos mediante un lock file local.
- Si mas adelante se quiere un trigger real por cambios, hay que sumar change
  notifications de Graph y un endpoint publico aparte.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, time as datetime_time
from pathlib import Path
from typing import Any, Optional

from agent.config import active_source_dir, load_settings
from agent.logging_config import setup_logging
from agent.memory.vector_store import PlateIndex
from agent.sources.sharepoint_client import SharePointClient


logger = logging.getLogger(__name__)


@dataclass
class LockHandle:
    """Representa el lock local usado por el scheduler."""

    file_descriptor: int
    path: Path


def _parse_hhmm(value: str) -> datetime_time:
    """Parsea `HH:MM` para la ventana laboral del scheduler."""
    raw = (value or "").strip()
    try:
        hour_str, minute_str = raw.split(":", 1)
        return datetime_time(hour=int(hour_str), minute=int(minute_str))
    except ValueError as exc:
        raise ValueError(f"Hora invalida para scheduler SharePoint: {value}") from exc


def _slot_key(now: datetime, interval_minutes: int) -> str:
    """Calcula la clave de slot para evitar multiples corridas por intervalo."""
    minute = (now.minute // interval_minutes) * interval_minutes
    slot = now.replace(minute=minute, second=0, microsecond=0)
    return slot.isoformat(timespec="minutes")


def _state_path(cache_dir: Path) -> Path:
    """Ubica el archivo de estado del scheduler."""
    return cache_dir / ".scheduler_state.json"


def _lock_path(cache_dir: Path) -> Path:
    """Ubica el lock file del scheduler."""
    return cache_dir / ".scheduler.lock"


def _load_state(path: Path) -> dict[str, Any]:
    """Carga el estado del scheduler si existe."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Estado del scheduler invalido en %s; se recreara", path)
        return {}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    """Guarda el estado del scheduler en disco."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")


def _acquire_lock(path: Path, stale_minutes: int) -> Optional[LockHandle]:
    """Adquiere un lock local simple para evitar corridas solapadas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        age_seconds = max(0.0, time.time() - path.stat().st_mtime)
        if age_seconds > stale_minutes * 60:
            logger.warning(
                "Lock SharePoint obsoleto detectado en %s; se reemplaza", path
            )
            path.unlink(missing_ok=True)
        else:
            return None

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    file_descriptor = os.open(str(path), flags)
    payload = {
        "pid": os.getpid(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    os.write(file_descriptor, json.dumps(payload, ensure_ascii=True).encode("utf-8"))
    return LockHandle(file_descriptor=file_descriptor, path=path)


def _release_lock(handle: Optional[LockHandle]) -> None:
    """Libera el lock del scheduler si estaba adquirido."""
    if handle is None:
        return
    try:
        os.close(handle.file_descriptor)
    finally:
        handle.path.unlink(missing_ok=True)


def _within_window(now: datetime, start: datetime_time, end: datetime_time) -> bool:
    """Evalua si la hora actual esta dentro de la ventana laboral."""
    current = now.time().replace(second=0, microsecond=0)
    return start <= current < end


def run_sync_cycle(*, ignore_window: bool = False, force_slot: bool = False) -> dict[str, Any]:
    """Ejecuta una corrida incremental SharePoint + indexado.

    La corrida hace:
    - sync incremental de SharePoint al mirror local
    - indexado solo de PDFs descargados, salvo que haya eliminaciones
    - persistencia de estado por slot para evitar duplicados
    """
    settings = load_settings()
    if settings.source_mode != "sharepoint":
        raise RuntimeError(
            "El scheduler SharePoint requiere PATENTES_SOURCE_MODE=sharepoint"
        )

    now = datetime.now()
    start = _parse_hhmm(settings.sharepoint.sync_window_start)
    end = _parse_hhmm(settings.sharepoint.sync_window_end)
    weekdays = settings.sharepoint.sync_weekdays
    interval = settings.sharepoint.sync_interval_minutes
    slot = _slot_key(now, interval)
    state_path = _state_path(settings.sharepoint.cache_dir)
    state = _load_state(state_path)

    if not ignore_window:
        if now.weekday() not in weekdays:
            return {
                "action": "skipped",
                "reason": "outside_weekdays",
                "weekday": now.weekday(),
                "allowed_weekdays": list(weekdays),
                "evaluated_at": now.isoformat(timespec="seconds"),
            }
        if not _within_window(now, start, end):
            return {
                "action": "skipped",
                "reason": "outside_window",
                "window_start": settings.sharepoint.sync_window_start,
                "window_end": settings.sharepoint.sync_window_end,
                "evaluated_at": now.isoformat(timespec="seconds"),
            }

    if not force_slot and state.get("last_completed_slot") == slot:
        return {
            "action": "skipped",
            "reason": "slot_already_completed",
            "slot": slot,
            "evaluated_at": now.isoformat(timespec="seconds"),
        }

    lock = _acquire_lock(_lock_path(settings.sharepoint.cache_dir), stale_minutes=180)
    if lock is None:
        return {
            "action": "skipped",
            "reason": "lock_active",
            "slot": slot,
            "evaluated_at": now.isoformat(timespec="seconds"),
        }

    try:
        with SharePointClient.from_settings(settings) as client:
            sharepoint_sync = client.sync_folder_to_cache(force=False, limit=None)

        deleted_paths = sharepoint_sync.get("deleted_relative_paths") or []
        changed_paths = [
            Path(path).resolve()
            for path in (sharepoint_sync.get("changed_local_paths") or [])
        ]

        index_payload: dict[str, Any]
        if sharepoint_sync["downloaded"] == 0 and not deleted_paths:
            index_payload = {
                "action": "skipped",
                "reason": "no_remote_changes",
            }
        else:
            index = PlateIndex(settings.index_db, active_source_dir(settings))
            if deleted_paths:
                index_stats = index.index_source(force=False)
            else:
                index_stats = index.index_source(force=False, pdf_paths=changed_paths)
            index_payload = {
                "action": "indexed",
                "stats": index_stats,
            }

        state.update(
            {
                "last_completed_slot": slot,
                "last_run_at": now.isoformat(timespec="seconds"),
                "last_sharepoint_sync": {
                    "downloaded": sharepoint_sync["downloaded"],
                    "skipped": sharepoint_sync["skipped"],
                    "deleted": sharepoint_sync["deleted"],
                    "requests": sharepoint_sync["telemetry"]["graph_requests_total"],
                    "bytes_downloaded_mb": sharepoint_sync["telemetry"]["bytes_downloaded_mb"],
                },
            }
        )
        _save_state(state_path, state)

        payload = {
            "action": "completed",
            "slot": slot,
            "evaluated_at": now.isoformat(timespec="seconds"),
            "schedule": {
                "interval_minutes": interval,
                "window_start": settings.sharepoint.sync_window_start,
                "window_end": settings.sharepoint.sync_window_end,
                "weekdays": list(weekdays),
            },
            "sharepoint_sync": sharepoint_sync,
            "index": index_payload,
        }
        logger.info(
            "Scheduler SharePoint completado | slot=%s | descargados=%s | eliminados=%s | index_action=%s",
            slot,
            sharepoint_sync["downloaded"],
            sharepoint_sync["deleted"],
            index_payload["action"],
        )
        return payload
    finally:
        _release_lock(lock)


def main() -> None:
    """Ejecuta el scheduler SharePoint en modo daemon o una sola corrida."""
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Scheduler incremental SharePoint para mirror + indexado"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Evalua el slot actual una sola vez y sale",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Ignora ventana/slot y ejecuta una sola corrida inmediata",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=30,
        help="Frecuencia de evaluacion en modo continuo",
    )
    args = parser.parse_args()

    if args.once or args.run_now:
        payload = run_sync_cycle(ignore_window=args.run_now, force_slot=args.run_now)
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return

    while True:
        payload = run_sync_cycle(ignore_window=False, force_slot=False)
        if payload.get("action") == "completed" or payload.get("reason") == "lock_active":
            print(json.dumps(payload, indent=2, ensure_ascii=True))
        time.sleep(max(5, args.poll_seconds))


if __name__ == "__main__":
    main()
