"""Aplicacion FastAPI del adaptador Webex.

Instrucciones:
- Este servicio solo resuelve transporte Webex -> backend Patentes.
- No duplica la logica del agente ni accede directamente al indice SQLite.
- Mantene healthcheck, webhook y arranque bien definidos.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request

from agent.logging_config import setup_logging
from webex_adapter.client import PatentesApiClient, RemoteCallError, WebexApiClient
from webex_adapter.config import load_settings
from webex_adapter.dedupe import WebexEventDedupeStore
from webex_adapter.schemas import ProcessedEventResult
from webex_adapter.service import WebexBridgeService
from webex_adapter.webhook_handler import (
    InvalidWebhookSignatureError,
    WebexWebhookHandler,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa clientes HTTP y dependencias del adaptador."""
    setup_logging()
    settings = load_settings()

    webex_http = httpx.AsyncClient(
        base_url=f"{settings.webex_api_base_url}/",
        headers={"Authorization": f"Bearer {settings.webex_bot_token}"},
        timeout=settings.webex_request_timeout_seconds,
    )
    patents_http = httpx.AsyncClient(
        base_url=f"{settings.patents_api_base_url}/",
        timeout=settings.patents_api_timeout_seconds,
    )

    webex_client = WebexApiClient(webex_http)
    patents_client = PatentesApiClient(patents_http)
    dedupe_store = WebexEventDedupeStore(settings.dedupe_store)
    bot_identity = await webex_client.get_me()
    service = WebexBridgeService(
        settings,
        webex_client,
        patents_client,
        dedupe_store,
        bot_identity=bot_identity,
    )
    handler = WebexWebhookHandler(settings, service)

    app.state.settings = settings
    app.state.handler = handler
    app.state.webex_http = webex_http
    app.state.patents_http = patents_http

    bot_name = bot_identity.get("displayName") or bot_identity.get("id") or "desconocido"
    logger.info(
        "Adaptador Webex listo | bot=%s | api=%s | dedupe=%s",
        bot_name,
        settings.patents_api_base_url,
        settings.dedupe_store,
    )
    try:
        yield
    finally:
        await webex_http.aclose()
        await patents_http.aclose()


app = FastAPI(
    title="Adaptador Webex del agente de patentes",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/webex/health")
async def health(request: Request) -> dict[str, object]:
    """Devuelve el estado minimo del adaptador sin exponer secretos."""
    settings = request.app.state.settings
    return {
        "status": "ok",
        "patentes_api_base_url": settings.patents_api_base_url,
        "allowed_room_types": list(settings.allowed_room_types),
        "dedupe_store": str(settings.dedupe_store),
    }


@app.post("/webex/webhook", response_model=ProcessedEventResult)
async def webex_webhook(request: Request) -> ProcessedEventResult:
    """Recibe eventos Webex y los reenvia al backend del agente."""
    raw_body = await request.body()
    handler: WebexWebhookHandler = request.app.state.handler
    try:
        return await handler.handle(raw_body, request.headers)
    except InvalidWebhookSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RemoteCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
