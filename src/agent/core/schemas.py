"""Esquemas de datos internos para el agente de patentes.

Instrucciones:
- Mantene los esquemas estables para evitar romper herramientas y casos de evaluacion.
- Agrega nuevos campos con cuidado y actualiza las pruebas.
- Usa estas clases de datos como referencia unica de las respuestas del agente.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PlateHit:
    """Resultado de una coincidencia de patente con metadatos de paginas."""
    plate: str
    document_path: str
    page_number: int
    snippet: str
    document_link: str
    match_type: str = "exacto"
    poliza: Optional[str] = None
    certificado: Optional[str] = None
    asegurado: Optional[str] = None
    vigencia_desde: Optional[str] = None
    vigencia_hasta: Optional[str] = None
    vehiculo: Optional[str] = None
    cobertura: Optional[str] = None
    dominio_label: Optional[str] = None
    label_pages: Optional[Dict[str, List[int]]] = None


@dataclass(frozen=True)
class PlateSearchResult:
    """Respuesta normalizada de una busqueda de patentes."""
    plate: str
    found: bool
    results: List[PlateHit]
    message: Optional[str] = None
