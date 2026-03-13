"""Memoria de corto plazo respaldada por sesiones ADK.

Instrucciones:
- Mantene este modulo enfocado en el almacenamiento de sesiones.
- No agregues logica de negocio aqui.
- La persistencia es local y se usa solo para desarrollo o demostraciones.
- Usa metodos async cuando existan para evitar warnings deprecados.
"""

import json
import logging
from pathlib import Path

try:
    from google.adk.sessions import InMemorySessionService
except ImportError:
    InMemorySessionService = None


logger = logging.getLogger(__name__)


class PersistentInMemorySessionService(InMemorySessionService):
    """Servicio de sesiones en memoria con persistencia en disco.

    Guarda el estado de sesiones en un archivo JSON simple.
    """

    def __init__(self, store_path: Path, app_name: str):
        super().__init__()
        self.store_path = store_path
        self.app_name = app_name
        self._load()

    def _load(self):
        """Carga sesiones guardadas en disco si existen."""
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            for record in data:
                if record.get("app_name") != self.app_name:
                    continue
                user_id = record.get("user_id")
                session_id = record.get("session_id")
                state = record.get("state")
                if user_id and session_id:
                    try:
                        self.create_session_sync(
                            app_name=self.app_name,
                            user_id=user_id,
                            session_id=session_id,
                            state=state,
                        )
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning("Fallo al cargar sesiones: %s", exc)

    def _persist_sync(self):
        """Persiste las sesiones actuales a disco (sync)."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            records = []
            for sess in self.list_sessions_sync(app_name=self.app_name):
                records.append(
                    {
                        "app_name": getattr(sess, "app_name", None),
                        "user_id": getattr(sess, "user_id", None),
                        "session_id": getattr(sess, "session_id", None),
                        "state": getattr(sess, "state", None),
                    }
                )
            self.store_path.write_text(json.dumps(records), encoding="utf-8")
        except Exception as exc:
            logger.warning("Fallo al persistir sesiones: %s", exc)

    async def _persist_async(self):
        """Persiste las sesiones actuales a disco (async)."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            records = []
            sessions = await self.list_sessions(app_name=self.app_name)
            for sess in sessions:
                records.append(
                    {
                        "app_name": getattr(sess, "app_name", None),
                        "user_id": getattr(sess, "user_id", None),
                        "session_id": getattr(sess, "session_id", None),
                        "state": getattr(sess, "state", None),
                    }
                )
            self.store_path.write_text(json.dumps(records), encoding="utf-8")
        except Exception as exc:
            logger.warning("Fallo al persistir sesiones: %s", exc)

    async def create_session(self, *, app_name: str, user_id: str, state=None, session_id=None):
        """Crea una sesion y persiste el estado."""
        sess = await super().create_session(app_name=app_name, user_id=user_id, state=state, session_id=session_id)
        await self._persist_async()
        return sess

    def create_session_sync(self, *, app_name: str, user_id: str, state=None, session_id=None):
        """Crea una sesion en modo sincronico y persiste el estado."""
        sess = super().create_session_sync(app_name=app_name, user_id=user_id, state=state, session_id=session_id)
        self._persist_sync()
        return sess

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str):
        """Elimina una sesion y persiste el estado."""
        await super().delete_session(app_name=app_name, user_id=user_id, session_id=session_id)
        await self._persist_async()

    def delete_session_sync(self, *, app_name: str, user_id: str, session_id: str):
        """Elimina una sesion en modo sincronico y persiste el estado."""
        super().delete_session_sync(app_name=app_name, user_id=user_id, session_id=session_id)
        self._persist_sync()


def make_session_service(store_path: Path, app_name: str):
    """Crea el servicio de sesiones por defecto (en memoria con persistencia)."""
    if not InMemorySessionService:
        raise ImportError("google.adk.sessions no esta disponible")
    return PersistentInMemorySessionService(store_path, app_name)
