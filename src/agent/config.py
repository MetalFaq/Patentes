"""Cargador de configuracion para el agente de patentes.

Instrucciones:
- Lee la configuracion desde variables de entorno o .env.
- Valida la presencia de GOOGLE_API_KEY y falla rapido si falta.
- Mantene las rutas por defecto relativas a la raiz del proyecto.
- Nunca registres ni incrustes claves de API.
- Este modulo define el origen de verdad de la configuracion del proyecto.
- Soporta fuente local y sincronizacion previa desde SharePoint hacia cache local.
- Tambien concentra los parametros de polling incremental para SharePoint.
"""

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional
from dotenv import load_dotenv


@dataclass(frozen=True)
class SharePointSettings:
    """Configuracion necesaria para sincronizar PDFs desde SharePoint.

    Se mantiene separada de `Settings` para dejar claro que solo aplica cuando
    `source_mode == "sharepoint"`.
    """

    tenant_id: Optional[str]
    client_id: Optional[str]
    site_url: Optional[str]
    library_name: Optional[str]
    folder_path: Optional[str]
    cert_thumbprint: Optional[str]
    cert_pfx_path: Optional[Path]
    cert_pfx_password: Optional[str]
    cache_dir: Path
    request_timeout_seconds: int
    graph_base_url: str
    sync_interval_minutes: int
    sync_window_start: str
    sync_window_end: str
    sync_weekdays: tuple[int, ...]


@dataclass(frozen=True)
class Settings:
    source_mode: str
    google_api_key: str
    app_name: str
    source_dir: Path
    index_db: Path
    session_store: Path
    transcript_store: Path
    sharepoint: SharePointSettings


def project_root() -> Path:
    """Devuelve la carpeta raiz del proyecto.

    Se usa para construir rutas relativas en entornos locales sin depender
    de variables externas.
    """
    return Path(__file__).resolve().parents[3]


def normalize_source_mode(value: Optional[str]) -> str:
    """Normaliza el modo de fuente aceptado por el proyecto."""
    mode = (value or "local").strip().lower()
    return mode if mode in {"local", "sharepoint"} else "local"


def parse_weekdays(value: Optional[str]) -> tuple[int, ...]:
    """Parsea una lista de dias de semana para el scheduler SharePoint.

    Espera valores tipo `0,1,2,3,4`, donde:
    - 0 = lunes
    - 6 = domingo
    """
    raw = (value or "0,1,2,3,4").strip()
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    weekdays = []
    for part in parts:
        try:
            day = int(part)
        except ValueError:
            continue
        if 0 <= day <= 6 and day not in weekdays:
            weekdays.append(day)
    return tuple(weekdays or [0, 1, 2, 3, 4])


def active_source_dir(settings: Optional[Settings] = None) -> Path:
    """Devuelve la carpeta activa desde la cual el proyecto sirve/indexa PDFs.

    - `local`: usa `PATENTES_SOURCE_DIR`.
    - `sharepoint`: usa el mirror/cache local sincronizado desde Graph.
    """
    current = settings or load_settings()
    if current.source_mode == "sharepoint":
        return current.sharepoint.cache_dir
    return current.source_dir


def load_settings() -> Settings:
    """Carga la configuracion desde .env y variables de entorno.

    Flujo:
    - Resuelve la raiz del proyecto.
    - Lee APP_NAME, GOOGLE_API_KEY, modo de fuente y rutas configurables.
    - Aplica valores seguros cuando no hay variables definidas.
    """
    load_dotenv()
    root = project_root()

    app_name = os.getenv("APP_NAME", "patentes_agent")
    source_mode = normalize_source_mode(os.getenv("PATENTES_SOURCE_MODE", "local"))
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise ValueError("Falta GOOGLE_API_KEY en el entorno")

    source_dir = Path(
        os.getenv("PATENTES_SOURCE_DIR", str(root.parent / "Fuente"))
    ).resolve()
    index_db = Path(
        os.getenv("PATENTES_INDEX_DB", str(root / "data" / "index" / "patentes.sqlite"))
    ).resolve()
    session_store = Path(
        os.getenv("PATENTES_SESSION_STORE", str(root / "data" / "session_store.json"))
    ).resolve()
    transcript_store = Path(
        os.getenv("PATENTES_TRANSCRIPT_PATH", str(root / "data" / "conversations.jsonl"))
    ).resolve()
    sharepoint_cache_dir = Path(
        os.getenv("SHAREPOINT_CACHE_DIR", str(root / "data" / "sharepoint_cache"))
    ).resolve()
    sharepoint = SharePointSettings(
        tenant_id=os.getenv("SHAREPOINT_TENANT_ID"),
        client_id=os.getenv("SHAREPOINT_CLIENT_ID"),
        site_url=os.getenv("SHAREPOINT_SITE_URL"),
        library_name=os.getenv("SHAREPOINT_LIBRARY_NAME"),
        folder_path=os.getenv("SHAREPOINT_FOLDER_PATH"),
        cert_thumbprint=os.getenv("SHAREPOINT_CERT_THUMBPRINT"),
        cert_pfx_path=(
            Path(os.getenv("SHAREPOINT_CERT_PFX_PATH")).resolve()
            if os.getenv("SHAREPOINT_CERT_PFX_PATH")
            else None
        ),
        cert_pfx_password=os.getenv("SHAREPOINT_CERT_PFX_PASSWORD"),
        cache_dir=sharepoint_cache_dir,
        request_timeout_seconds=int(os.getenv("SHAREPOINT_REQUEST_TIMEOUT_SECONDS", "60")),
        graph_base_url=os.getenv(
            "SHAREPOINT_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0"
        ).rstrip("/"),
        sync_interval_minutes=max(
            1, int(os.getenv("SHAREPOINT_SYNC_INTERVAL_MINUTES", "10"))
        ),
        sync_window_start=os.getenv("SHAREPOINT_SYNC_WINDOW_START", "08:00"),
        sync_window_end=os.getenv("SHAREPOINT_SYNC_WINDOW_END", "17:00"),
        sync_weekdays=parse_weekdays(os.getenv("SHAREPOINT_SYNC_WEEKDAYS")),
    )

    # Asegura que la variable de entorno este presente para las librerias que la requieren.
    os.environ.setdefault("GOOGLE_API_KEY", google_key)

    return Settings(
        source_mode=source_mode,
        google_api_key=google_key,
        app_name=app_name,
        source_dir=source_dir,
        index_db=index_db,
        session_store=session_store,
        transcript_store=transcript_store,
        sharepoint=sharepoint,
    )
