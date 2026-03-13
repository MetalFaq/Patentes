"""Configuracion del adaptador Webex del agente de patentes.

Instrucciones:
- Lee variables desde `.env` o el entorno del proceso.
- Valida los secretos minimos para poder consumir Webex y el backend Patentes.
- Mantene rutas relativas al proyecto para stores locales.
- No registres tokens ni secretos en logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from agent.config import project_root


@dataclass(frozen=True)
class WebexAdapterSettings:
    webex_bot_token: str
    webex_webhook_secret: str | None
    webex_api_base_url: str
    webex_request_timeout_seconds: float
    patents_api_base_url: str
    patents_api_timeout_seconds: float
    dedupe_store: Path
    dedupe_ttl_hours: int
    allowed_room_types: tuple[str, ...]


def _parse_room_types(raw_value: str | None) -> tuple[str, ...]:
    if not raw_value:
        return ("direct", "group")
    values = [item.strip().lower() for item in raw_value.split(",") if item.strip()]
    return tuple(values or ["direct", "group"])


def load_settings() -> WebexAdapterSettings:
    """Carga la configuracion del adaptador Webex.

    Requiere:
    - `WEBEX_BOT_TOKEN`
    - `PATENTES_API_BASE_URL`

    El resto de los campos tienen defaults seguros para desarrollo local.
    """
    load_dotenv()
    root = project_root()

    bot_token = os.getenv("WEBEX_BOT_TOKEN")
    if not bot_token:
        raise ValueError("Falta WEBEX_BOT_TOKEN en el entorno")

    patents_api_base_url = os.getenv("PATENTES_API_BASE_URL", "http://localhost:8000").rstrip("/")
    if not patents_api_base_url:
        raise ValueError("Falta PATENTES_API_BASE_URL en el entorno")

    dedupe_store = Path(
        os.getenv(
            "WEBEX_DEDUPE_STORE",
            str(root / "data" / "webex_adapter" / "webex_events.sqlite"),
        )
    ).resolve()

    return WebexAdapterSettings(
        webex_bot_token=bot_token,
        webex_webhook_secret=os.getenv("WEBEX_WEBHOOK_SECRET") or None,
        webex_api_base_url=os.getenv("WEBEX_API_BASE_URL", "https://webexapis.com/v1").rstrip("/"),
        webex_request_timeout_seconds=float(os.getenv("WEBEX_REQUEST_TIMEOUT_SECONDS", "30")),
        patents_api_base_url=patents_api_base_url,
        patents_api_timeout_seconds=float(os.getenv("PATENTES_API_TIMEOUT_SECONDS", "60")),
        dedupe_store=dedupe_store,
        dedupe_ttl_hours=int(os.getenv("WEBEX_DEDUPE_TTL_HOURS", "72")),
        allowed_room_types=_parse_room_types(os.getenv("WEBEX_ALLOWED_ROOM_TYPES")),
    )
