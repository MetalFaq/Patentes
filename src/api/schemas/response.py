"""Esquemas de respuesta para la API de chat.

Instrucciones:
- Mantene los campos de respuesta estables para clientes de la API.
- Evita cambios de formato sin versionar.
- Los datos de depuracion son solo trazas tecnicas de herramientas.
- El campo `text` puede incluir markdown con enlaces a documentos.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Respuesta del agente.

    Campo:
    - text: texto de respuesta del agente.
    """

    text: str = Field(
        ...,
        description="Texto de respuesta del agente; puede incluir markdown",
    )


class ChatDebugResponse(BaseModel):
    """Respuesta del agente con datos de depuracion.

    Campos:
    - text: texto de respuesta del agente.
    - debug: informacion tecnica de herramientas y coincidencias.
    """

    text: str = Field(
        ...,
        description="Texto de respuesta del agente; puede incluir markdown",
    )
    debug: Dict[str, Any] = Field(..., description="Datos de depuracion")
