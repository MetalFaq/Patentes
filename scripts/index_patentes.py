"""Comando de consola para construir o actualizar el indice de patentes.

Instrucciones:
- Ejecuta esto antes de usar el agente y cada vez que cambien los PDFs.
- Usa las opciones para pruebas rapidas o para acotar el trabajo por sitio.
- Si hay errores, revisar permisos de lectura y la ruta de PATENTES_SOURCE_DIR.
- Errores de extraccion se registran en patentes_agent.index_errors.log.
- La salida es un resumen JSON con totales y tiempos de indexado.
- Se insertan solo dominios validos (AAA999 o AA999AA).
"""

import argparse
import json

from agent.config import load_settings
from agent.logging_config import setup_logging
from agent.memory.vector_store import PlateIndex


def main() -> None:
    """Indexa PDFs y deja estadisticas en consola.

    Flujo:
    - Lee configuracion desde .env y prepara el registro.
    - Construye o actualiza el indice local en SQLite.
    - Aplica limites opcionales para acelerar pruebas.
    - Imprime un resumen JSON con totales, tiempo total y tiempos por PDF.
    """
    setup_logging()
    parser = argparse.ArgumentParser(description="Indexa PDFs para busqueda de patentes")
    parser.add_argument("--force", action="store_true", help="Reindexa todos los PDFs")
    parser.add_argument("--limit", type=int, default=None, help="Limita la cantidad de PDFs")
    parser.add_argument(
        "--max-pages-per-pdf",
        type=int,
        default=None,
        help="Limita paginas por PDF",
    )
    parser.add_argument(
        "--site",
        type=str,
        default=None,
        help="Subcarpeta dentro de la fuente a procesar",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=10,
        help="Registra progreso cada N PDFs",
    )
    args = parser.parse_args()

    settings = load_settings()
    index = PlateIndex(settings.index_db, settings.source_dir)
    stats = index.index_source(
        force=args.force,
        limit=args.limit,
        max_pages_per_pdf=args.max_pages_per_pdf,
        site=args.site,
        log_every=args.log_every,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
