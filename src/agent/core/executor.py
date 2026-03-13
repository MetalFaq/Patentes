"""Ejecutor de reemplazo para el agente de patentes.

Instrucciones:
- Centraliza las llamadas a herramientas aqui si agregas planificacion.
- Mantene la logica de ejecucion simple y observable.
- Usa este modulo como punto de extension para flujos mas complejos.
"""

from typing import Iterable, List


def execute_plan(plan: Iterable[str]) -> List[str]:
    """Devuelve los pasos del plan por ahora.

    Este ejecutor es un reemplazo provisorio que expone el contrato esperado.
    """
    return list(plan)
