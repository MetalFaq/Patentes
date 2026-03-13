"""Cargador de configuracion para el agente de patentes.

Instrucciones:
- Lee la configuracion desde variables de entorno o .env.
- Valida la presencia de GOOGLE_API_KEY y falla rapido si falta.
- Mantene las rutas por defecto relativas a la raiz del proyecto.
- Nunca registres ni incrustes claves de API.
- Este modulo define el origen de verdad de la configuracion del proyecto.
"""

from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    app_name: str
    source_dir: Path
    index_db: Path
    session_store: Path
    transcript_store: Path


def project_root() -> Path:
    """Devuelve la carpeta raiz del proyecto.

    Se usa para construir rutas relativas en entornos locales sin depender
    de variables externas.
    """
    return Path(__file__).resolve().parents[3]


def load_settings() -> Settings:
    """Carga la configuracion desde .env y variables de entorno.

    Flujo:
    - Resuelve la raiz del proyecto.
    - Lee APP_NAME, GOOGLE_API_KEY y rutas configurables.
    - Aplica valores seguros cuando no hay variables definidas.
    """
    load_dotenv()
    root = project_root()

    app_name = os.getenv("APP_NAME", "patentes_agent")
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

    # Asegura que la variable de entorno este presente para las librerias que la requieren.
    os.environ.setdefault("GOOGLE_API_KEY", google_key)

    return Settings(
        google_api_key=google_key,
        app_name=app_name,
        source_dir=source_dir,
        index_db=index_db,
        session_store=session_store,
        transcript_store=transcript_store,
    )
