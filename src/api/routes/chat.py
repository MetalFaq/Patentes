"""Ruta de API de chat para el agente de patentes.

Instrucciones:
- Mantene esta ruta delgada.
- Delega la logica de negocio al modulo del agente.
- Valida entrada y salida con esquemas.
- /chat es el contrato estable consumido por UI, CLI y adaptador Webex.
- /chat_debug devuelve trazas tecnicas de herramientas.
"""

from fastapi import APIRouter, Depends

from agent.core.agent import run_agent_message
from api.dependencies import get_agent, get_session_service, get_settings
from api.schemas.request import ChatRequest
from api.schemas.response import ChatDebugResponse, ChatResponse
from agent.debug_trace import clear_trace, get_trace, start_trace


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    agent=Depends(get_agent),
    session_service=Depends(get_session_service),
    settings=Depends(get_settings),
) -> ChatResponse:
    """Procesa un mensaje de chat y devuelve la respuesta del agente.

    La respuesta es texto y puede incluir markdown con enlaces a PDFs.
    """
    text = run_agent_message(
        agent,
        session_service,
        app_name=settings.app_name,
        user_id=request.user_id,
        session_id=request.session_id,
        message_text=request.message,
    )
    return ChatResponse(text=text)


@router.post("/chat_debug", response_model=ChatDebugResponse)
def chat_debug(
    request: ChatRequest,
    agent=Depends(get_agent),
    session_service=Depends(get_session_service),
    settings=Depends(get_settings),
) -> ChatDebugResponse:
    """Procesa un mensaje y devuelve respuesta con datos de depuracion."""
    start_trace()
    try:
        text = run_agent_message(
            agent,
            session_service,
            app_name=settings.app_name,
            user_id=request.user_id,
            session_id=request.session_id,
            message_text=request.message,
        )
        debug = {"tools": get_trace()}
    finally:
        clear_trace()
    return ChatDebugResponse(text=text, debug=debug)
