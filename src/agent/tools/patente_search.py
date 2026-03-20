"""Herramientas para la busqueda de patentes.

Instrucciones:
- Esta es la unica herramienta expuesta al agente para buscar documentos.
- No saltees el indice aqui.
- Valida entradas y devolve mensajes claros.
- El modo fuzzy es explicito y puede generar falsos positivos.
"""

from typing import Dict, List

from agent.config import active_source_dir, load_settings
from agent.debug_trace import append_trace
from agent.memory.vector_store import PlateIndex, normalize_plate


_INDEX: PlateIndex | None = None


def _get_index() -> PlateIndex:
    """Inicializa el indice en memoria si aun no existe.

    Si la fuente activa es SharePoint, el indice trabaja sobre el cache local
    sincronizado previamente.
    """
    global _INDEX
    if _INDEX is None:
        settings = load_settings()
        _INDEX = PlateIndex(settings.index_db, active_source_dir(settings))
    return _INDEX


def buscar_patente(
    placa: str,
    max_resultados: int = 5,
    modo: str = "exacto",
) -> Dict[str, object]:
    """Buscar una patente en el indice local y devolver enlaces con pagina.

    Retorna:
    - found: indica si hubo resultados.
    - plate: patente normalizada.
    - results: lista con datos, enlaces, campos extraidos y tipo de coincidencia (match_type).
    - modo: exacto, prefijo, contiene o fuzzy.
    - dominio_label: etiqueta detectada (DOMINIO, PATENTE, MATRICULA o PLACA).
    - label_pages: paginas agrupadas por etiqueta.
    """
    plate_norm = normalize_plate(placa or "")
    if not plate_norm:
        return {
            "found": False,
            "message": "Patente vacia o invalida.",
            "results": [],
        }

    modo_norm = (modo or "exacto").strip().lower()
    if modo_norm not in {"exacto", "prefijo", "contiene", "fuzzy"}:
        return {
            "found": False,
            "message": "Modo invalido. Usa exacto, prefijo, contiene o fuzzy.",
            "results": [],
        }

    index = _get_index()
    if not index.db_path.exists():
        return {
            "found": False,
            "message": "Indice no encontrado. Ejecuta scripts/index_patentes.py para generarlo.",
            "results": [],
        }

    hits = index.search(plate_norm, limit=max_resultados, mode=modo_norm)
    results: List[Dict[str, object]] = []
    for hit in hits:
        plate_norm_hit = normalize_plate(hit.plate)
        label_pages = index.get_label_pages(plate_norm_hit)
        results.append(
            {
                "plate": hit.plate,
                "document_path": hit.document_path,
                "page_number": hit.page_number,
                "document_link": hit.document_link,
                "snippet": hit.snippet,
                "match_type": hit.match_type,
                "poliza": hit.poliza,
                "certificado": hit.certificado,
                "asegurado": hit.asegurado,
                "vigencia_desde": hit.vigencia_desde,
                "vigencia_hasta": hit.vigencia_hasta,
                "vehiculo": hit.vehiculo,
                "cobertura": hit.cobertura,
                "dominio_label": hit.dominio_label,
                "label_pages": label_pages,
            }
        )

    response = {
        "found": bool(results),
        "plate": plate_norm,
        "results": results,
        "modo": modo_norm,
    }
    append_trace(
        {
            "herramienta": "buscar_patente",
            "entrada": {"placa": placa, "max_resultados": max_resultados, "modo": modo_norm},
            "resultado": {
                "found": response["found"],
                "plate": response["plate"],
                "modo": response["modo"],
                "count": len(results),
                "match_types": [item.get("match_type") for item in results],
                "resultados": [
                    {
                        "plate": item.get("plate"),
                        "document_path": item.get("document_path"),
                        "page_number": item.get("page_number"),
                        "document_link": item.get("document_link"),
                        "match_type": item.get("match_type"),
                        "dominio_label": item.get("dominio_label"),
                        "label_pages": item.get("label_pages"),
                    }
                    for item in results
                ],
            },
        }
    )
    return response


def build_tools() -> List[object]:
    """Devuelve la lista de herramientas para el agente ADK."""
    return [buscar_patente]
