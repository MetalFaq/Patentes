"""Dependencias de FastAPI para el agente de patentes.

Instrucciones:
- Memoriza objetos pesados (agente, servicio de sesiones).
- No almacenes datos especificos de la solicitud aqui.
- Mantene estas dependencias puras y faciles de probar.
"""

from functools import lru_cache

from agent.config import Settings, load_settings
from agent.core.agent import create_agent
from agent.memory.short_term import make_session_service
from agent.tools.patente_search import build_tools


@lru_cache
def get_settings() -> Settings:
    """Devuelve configuracion cargada desde .env y variables de entorno."""
    return load_settings()


@lru_cache
def get_agent():
    """Construye y memoriza el agente con las herramientas disponibles."""
    tools = build_tools()
    return create_agent(tools)


@lru_cache
def get_session_service():
    """Crea y memoriza el servicio de sesiones para la API."""
    settings = get_settings()
    return make_session_service(settings.session_store, settings.app_name)
