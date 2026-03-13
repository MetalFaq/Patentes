"""Chat por consola para el agente de patentes.

Instrucciones:
- Usalo para pruebas locales sin levantar la API.
- Escribi 'exit' o 'quit' para salir.
- Sirve para validar instrucciones y herramientas rapidamente.
- Los modos prefijo/contiene/fuzzy se activan solo si el usuario los pide.
"""

import uuid

from agent.config import load_settings
from agent.core.agent import create_agent, run_agent_message
from agent.logging_config import setup_logging
from agent.memory.short_term import make_session_service
from agent.tools.patente_search import build_tools


def main() -> None:
    """Inicia un chat interactivo en consola con el agente.

    Flujo:
    - Carga configuracion y crea el agente con herramientas reales.
    - Abre una sesion local con un ID aleatorio.
    - Lee mensajes del usuario y devuelve respuestas del agente.
    - Deja un historial en consola para depuracion rapida.
    """
    setup_logging()
    settings = load_settings()
    agent = create_agent(build_tools())
    session_service = make_session_service(settings.session_store, settings.app_name)

    user_id = "cli_user"
    session_id = str(uuid.uuid4())

    print("Escribe una patente o 'exit' para salir.")
    while True:
        message = input("tu> ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue
        reply = run_agent_message(
            agent,
            session_service,
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id,
            message_text=message,
        )
        print(f"agente> {reply}")


if __name__ == "__main__":
    main()
