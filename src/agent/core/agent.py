"""Ensamblado del agente ADK y ayudas de ejecucion.

Instrucciones:
- Carga las instrucciones desde src/agent/prompts.
- Mantene el registro de herramientas centralizado aqui.
- Respeta GEMINI_MODEL y THINKING_LEVEL configurados en .env.
- No incrustes secretos en el codigo.
- Reporta errores en registros y devolve un texto seguro al usuario.
- Evita responder estadisticas globales si no hubo uso de herramientas.
- Registra trazas tecnicas para /chat_debug.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Callable, Iterable
import unicodedata

try:
    from google.adk.agents.llm_agent import Agent
    from google.adk.runners import Runner
    from google.genai import types
except ImportError as exc:
    raise ImportError("se requiere google-adk para el modulo del agente") from exc

from agent.debug_trace import clear_trace, ensure_trace, get_trace

logger = logging.getLogger(__name__)


def _strip_accents(text: str) -> str:
    """Normaliza texto removiendo acentos para comparaciones simples."""
    return "".join(
        char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn"
    )


def _looks_like_stats_request(message_text: str) -> bool:
    """Detecta pedidos de estadisticas globales fuera de una patente."""
    if not message_text:
        return False
    text = _strip_accents(message_text).lower()
    keywords = [
        "promedio",
        "media",
        "estadistica",
        "mas comun",
        "mas frecuente",
        "ranking",
        "top",
        "porcentaje",
        "distribucion",
        "cantidad de",
        "cuantas",
        "total de",
        "antiguedad",
        "marca y modelo",
        "modelo mas comun",
    ]
    return any(key in text for key in keywords)


def _prompt_dir() -> Path:
    """Devuelve la carpeta donde viven las instrucciones del agente."""
    return Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(name: str) -> str:
    """Carga un archivo de instrucciones por nombre."""
    path = _prompt_dir() / name
    return path.read_text(encoding="utf-8")


def build_instruction() -> str:
    """Combina instrucciones en una unica instruccion.

    Orden:
    - system.md
    - policies.md
    - tools.md
    """
    system = load_prompt("system.md")
    policies = load_prompt("policies.md")
    tools = load_prompt("tools.md")
    return "\n\n".join([system, policies, tools]).strip()


def create_agent(tools: Iterable[Callable]) -> Agent:
    """Crea un agente ADK con instrucciones y herramientas.

    Usa:
    - GEMINI_MODEL para el modelo.
    - THINKING_LEVEL para el nivel de razonamiento.
    """
    instruction = build_instruction()
    model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    thinking_level = os.getenv("THINKING_LEVEL", "low")
    thinking_config = None
    if thinking_level:
        try:
            thinking_config = types.ThinkingConfig(thinking_level=thinking_level)
        except Exception as exc:
            logger.warning("THINKING_LEVEL invalido (%s): %s", thinking_level, exc)
    generate_config = types.GenerateContentConfig(thinking_config=thinking_config)

    agent = Agent(
        model=model,
        name="patentes_seguro_agent",
        description="Agente para seguro de patentes de automoviles.",
        instruction=instruction,
        tools=list(tools),
        generate_content_config=generate_config,
    )
    return agent


async def _ensure_session(session_service, app_name: str, user_id: str, session_id: str):
    """Garantiza que exista una sesion para el usuario."""
    existing = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if existing is None:
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )


def run_agent_message(
    agent: Agent,
    session_service,
    *,
    app_name: str,
    user_id: str,
    session_id: str,
    message_text: str,
) -> str:
    """Ejecuta el agente para un mensaje del usuario y devuelve la respuesta en texto.

    - Crea un bucle aislado para evitar conflictos con FastAPI.
    - Consolida texto de eventos del Runner (ADK).
    - Registra errores y devuelve un mensaje controlado.
    - Bloquea estadisticas globales si no hubo uso de herramientas.
    """

    async def run_once():
        await _ensure_session(session_service, app_name, user_id, session_id)

        trace_started = ensure_trace()
        runner = Runner(
            agent=agent,
            app_name=app_name,
            session_service=session_service,
        )
        content = types.Content(parts=[types.Part(text=message_text)])

        final_text = ""
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                logger.info("Evento recibido: %s", type(event))
                if hasattr(event, "text") and event.text:
                    final_text += event.text
                elif hasattr(event, "parts"):
                    for part in event.parts:
                        if hasattr(part, "text") and part.text:
                            final_text += part.text
                elif hasattr(event, "content") and event.content:
                    try:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                final_text += part.text
                    except Exception:
                        pass
        except Exception:
            logger.exception("Fallo al ejecutar el agente")
            return "Ocurrio un error al ejecutar el agente. Revisa los registros."

        tools_trace = get_trace()
        if trace_started:
            clear_trace()

        if not tools_trace and _looks_like_stats_request(message_text):
            return (
                "No puedo calcular estadisticas globales sin datos estructurados. "
                "Este agente responde solo con informacion de patentes disponibles en el indice."
            )

        if not final_text:
            return "[El agente no envio texto de respuesta, revisa los registros]"
        return final_text

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_once())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
