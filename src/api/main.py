"""Aplicacion FastAPI para el backend del agente de patentes.

Instrucciones:
- Mantene este modulo minimo y enfocado en el cableado.
- Monta rutas, interceptores y registro centralizado.
- Deja la logica del agente en src/agent.
- Este backend es consumido por la UI de pruebas, la CLI y el adaptador Webex.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.routes.chat import router as chat_router
from api.routes.docs import router as docs_router
from api.routes.ui import router as ui_router
from agent.config import load_settings
from agent.logging_config import setup_logging
from agent.memory.transcript import append_transcript

app = FastAPI(title="API del agente de patentes", version="0.1.0")
app.include_router(chat_router)
app.include_router(docs_router)
app.include_router(ui_router)

logger = logging.getLogger(__name__)


class TranscriptMiddleware(BaseHTTPMiddleware):
    """Interceptor para registrar conversaciones en JSONL.

    Guarda mensajes de usuario y respuestas del agente para auditoria basica.
    Incluye un campo opcional `channel` para identificar el origen del mensaje.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/chat":
            return await call_next(request)

        body_bytes = await request.body()

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive)
        response = await call_next(request)

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            respuesta = json.loads(response_body.decode("utf-8")) if response_body else {}
            settings = load_settings()

            records: list[dict[str, Any]] = []
            user_id = payload.get("user_id")
            session_id = payload.get("session_id")
            user_text = payload.get("message")
            agent_text = respuesta.get("text")
            channel = payload.get("channel") or "api"

            if user_text:
                records.append(
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": "user",
                        "text": user_text,
                        "channel": channel,
                    }
                )
            if agent_text:
                records.append(
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": "assistant",
                        "text": agent_text,
                        "channel": channel,
                    }
                )

            for record in records:
                append_transcript(settings.transcript_store, record)
        except Exception:
            logger.exception("Fallo al registrar la transcripcion de chat")

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


@app.on_event("startup")
def startup_event() -> None:
    """Configura el registro al iniciar la aplicacion."""
    setup_logging()


app.add_middleware(TranscriptMiddleware)
