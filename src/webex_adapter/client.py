"""Clientes HTTP del adaptador Webex.

Instrucciones:
- Centraliza todas las llamadas a Webex y al backend Patentes.
- Registra tiempos, metodo, ruta y codigo HTTP sin imprimir secretos.
- Devuelve errores claros para que el handler responda con 5xx/4xx adecuados.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

import httpx

from webex_adapter.schemas import (
    PatentesChatRequest,
    PatentesChatResponse,
    WebexMessage,
)

logger = logging.getLogger(__name__)


class RemoteCallError(RuntimeError):
    """Error de integracion contra un servicio remoto."""


def _body_excerpt(response: httpx.Response) -> str:
    text = response.text.strip()
    if len(text) > 300:
        return text[:297] + "..."
    return text


class WebexApiClient:
    """Cliente asincronico para la API REST de Webex."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def _request_json(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        started = perf_counter()
        response = await self._http_client.request(method, path, **kwargs)
        elapsed = perf_counter() - started
        logger.info(
            "Webex %s %s -> %s | %.3fs",
            method.upper(),
            path,
            response.status_code,
            elapsed,
        )
        if response.status_code >= 400:
            raise RemoteCallError(
                f"Webex devolvio {response.status_code} para {method.upper()} {path}: {_body_excerpt(response)}"
            )
        return response.json()

    async def get_me(self) -> dict[str, Any]:
        """Devuelve la identidad del bot autenticado."""
        return await self._request_json("GET", "people/me")

    async def get_message(self, message_id: str) -> WebexMessage:
        """Recupera el detalle completo de un mensaje por id."""
        payload = await self._request_json("GET", f"messages/{message_id}")
        payload["raw"] = dict(payload)
        return WebexMessage.model_validate(payload)

    async def send_markdown_message(self, room_id: str, markdown: str) -> dict[str, Any]:
        """Publica una respuesta markdown en la sala indicada."""
        payload: dict[str, Any] = {"roomId": room_id}
        clean_markdown = markdown.strip()
        if clean_markdown:
            payload["markdown"] = clean_markdown
        else:
            payload["text"] = "[El backend no devolvio contenido]"
        return await self._request_json("POST", "messages", json=payload)


class PatentesApiClient:
    """Cliente asincronico para el backend `/chat` del agente de patentes."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def send_chat(self, payload: PatentesChatRequest) -> PatentesChatResponse:
        """Reenvia un mensaje a `POST /chat` y valida la respuesta."""
        started = perf_counter()
        response = await self._http_client.post("chat", json=payload.model_dump(exclude_none=True))
        elapsed = perf_counter() - started
        logger.info(
            "Patentes POST /chat -> %s | %.3fs | session=%s",
            response.status_code,
            elapsed,
            payload.session_id,
        )
        if response.status_code >= 400:
            raise RemoteCallError(
                f"Patentes devolvio {response.status_code} para POST /chat: {_body_excerpt(response)}"
            )
        return PatentesChatResponse.model_validate(response.json())
