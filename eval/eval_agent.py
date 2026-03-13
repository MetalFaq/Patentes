"""Ejecutor de evaluacion para el agente de patentes.

Instrucciones:
- Carga eval/conversations.json y ejecuta el agente contra cada caso.
- Agrega aserciones a medida que maduren las pruebas.
- Usalo para detectar regresiones cuando cambien instrucciones o herramientas.
- No es un ejecutor de produccion, solo un chequeo manual guiado.
- El agente responde en modo exacto salvo que el caso pida prefijo/contiene/fuzzy.
"""

import json
from pathlib import Path

from agent.config import load_settings
from agent.core.agent import create_agent, run_agent_message
from agent.memory.short_term import make_session_service
from agent.tools.patente_search import build_tools


def load_cases() -> list[dict]:
    """Lee los casos desde conversations.json y devuelve la lista.

    - Cada caso incluye un input y una expectativa textual.
    - Si falta la clave, devuelve una lista vacia.
    - Este auxiliar evita repetir logica de lectura en main().
    """
    data_path = Path(__file__).resolve().parent / "conversations.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    return data.get("cases", [])


def main() -> None:
    """Ejecuta todos los casos y muestra la respuesta del agente.

    Flujo:
    - Carga configuracion y crea el agente con sus herramientas reales.
    - Inicializa el servicio de sesiones (memoria de corto plazo).
    - Recorre cada caso y muestra la salida para revision manual.
    - Ideal para comparar resultados antes y despues de cambios.
    """
    settings = load_settings()
    agent = create_agent(build_tools())
    session_service = make_session_service(settings.session_store, settings.app_name)
    cases = load_cases()
    print(f"Cargados {len(cases)} casos de evaluacion.")

    for idx, case in enumerate(cases, start=1):
        user_message = case.get("input", "")
        response = run_agent_message(
            agent,
            session_service,
            app_name=settings.app_name,
            user_id="eval_user",
            session_id=f"eval_{idx}",
            message_text=user_message,
        )
        print(f"Caso {idx}: {user_message}\nRespuesta: {response}\n")


if __name__ == "__main__":
    main()
