"""Esquemas del adaptador Webex.

Instrucciones:
- Modela solo el subconjunto de datos que el adaptador necesita.
- Mantene estos modelos separados del backend Patentes para desacoplar el canal.
- No agregues campos sin documentarlos en `README.md`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class WebexWebhookData(BaseModel):
    """Subconjunto del payload `data` enviado por Webex."""

    id: str = Field(..., description="Identificador del mensaje en Webex")
    roomId: str = Field(..., description="Sala o espacio de Webex")
    personId: str | None = Field(default=None, description="Autor del mensaje")
    personEmail: str | None = Field(default=None, description="Email del autor")
    roomType: str | None = Field(default=None, description="Tipo de sala")


class WebexWebhookEvent(BaseModel):
    """Evento entrante del webhook de Webex."""

    id: str = Field(..., description="Identificador del evento webhook")
    name: str | None = Field(default=None, description="Nombre descriptivo del evento")
    resource: str = Field(..., description="Recurso de Webex, por ejemplo messages")
    event: str = Field(..., description="Tipo de evento, por ejemplo created")
    data: WebexWebhookData = Field(..., description="Datos del mensaje relacionado")


class WebexMessage(BaseModel):
    """Detalle completo del mensaje recuperado desde Webex."""

    id: str
    roomId: str
    roomType: str | None = None
    personId: str
    personEmail: str | None = None
    text: str | None = None
    markdown: str | None = None
    created: str | None = None
    raw: dict[str, Any] | None = None


class PatentesChatRequest(BaseModel):
    """Contrato saliente hacia `POST /chat` del backend Patentes."""

    user_id: str
    session_id: str
    message: str
    channel: str = "webex"


class PatentesChatResponse(BaseModel):
    """Respuesta esperada del backend Patentes."""

    text: str


class ProcessedEventResult(BaseModel):
    """Resultado resumido del procesamiento de un evento Webex."""

    status: Literal["processed", "ignored"]
    reason: str
    event_id: str | None = None
    message_id: str | None = None
    room_id: str | None = None
    session_id: str | None = None
