"""Rastro de depuracion para herramientas del agente.

Instrucciones:
- Solo almacenar eventos tecnicos (entradas y salidas de herramientas).
- No registrar secretos ni contenido sensible.
- Usar para diagnostico en entornos controlados.
- Se consume desde /chat_debug y la UI web de pruebas.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict, List, Optional


_TRACE: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "agent_debug_trace", default=None
)


def start_trace() -> None:
    """Inicializa un rastro vacio para la solicitud actual."""
    _TRACE.set([])


def ensure_trace() -> bool:
    """Inicializa el rastro solo si no existe.

    Retorna True si se creo un rastro nuevo.
    """
    if _TRACE.get() is None:
        _TRACE.set([])
        return True
    return False


def append_trace(event: Dict[str, Any]) -> None:
    """Agrega un evento al rastro si esta activo."""
    trace = _TRACE.get()
    if trace is None:
        return
    trace.append(event)


def get_trace() -> List[Dict[str, Any]]:
    """Devuelve el rastro actual (o una lista vacia si no existe)."""
    trace = _TRACE.get()
    return trace or []


def clear_trace() -> None:
    """Limpia el rastro para evitar fugas entre solicitudes."""
    _TRACE.set(None)
