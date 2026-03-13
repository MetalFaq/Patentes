"""Planificador opcional para el agente de patentes.

Instrucciones:
- Mantene esto deterministico y verificable.
- Si agregas un planificador real, actualiza los casos de evaluacion.
- El plan debe ser simple y reproducible para facilitar depuracion.
"""

from typing import List


def plan_steps(user_message: str) -> List[str]:
    """Devuelve un plan minimo de uso de herramientas.

    La salida se puede usar para registrar pasos o depurar instrucciones.
    """
    return ["interpretar_consulta", "usar_buscar_patente", "resumir_resultados"]
