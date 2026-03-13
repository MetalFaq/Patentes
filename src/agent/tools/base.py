"""Tipos comunes de herramientas para el agente de patentes.

Instrucciones:
- Mantene la entrada/salida de herramientas acotada y serializable en JSON.
- Agrega validacion cerca del limite de la herramienta.
- Usa estos tipos para mantener contratos consistentes.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ToolResult:
    """Resultado estandar de una herramienta."""
    ok: bool
    payload: Dict[str, Any]
