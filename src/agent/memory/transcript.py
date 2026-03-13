"""Persistencia simple de conversaciones en formato JSONL.

Instrucciones:
- Cada linea es un JSON con un mensaje (usuario o asistente).
- Usar para auditoria y depuracion basica.
- El registro puede incluir metadatos como `channel` para identificar el origen.
- No guardar secretos ni datos sensibles sin control.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def append_transcript(path: Path, record: Dict[str, Any]) -> None:
    """Agrega un registro al archivo JSONL.

    Si no hay marca de tiempo, la agrega en UTC.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(record)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
