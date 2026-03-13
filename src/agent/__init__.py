"""Paquete del agente de patentes.

Instrucciones:
- Mantene la logica del agente dentro de src/agent.
- No pongas codigo de API o interfaz aqui.
- Mantene secretos en .env, nunca los incrustes.
"""

def create_agent(*args, **kwargs):
    """Crea el agente ADK de forma diferida para evitar imports costosos."""
    from .core.agent import create_agent as _create_agent

    return _create_agent(*args, **kwargs)


def run_agent_message(*args, **kwargs):
    """Ejecuta el agente de forma diferida para evitar imports costosos."""
    from .core.agent import run_agent_message as _run_agent_message

    return _run_agent_message(*args, **kwargs)


__all__ = ["create_agent", "run_agent_message"]
