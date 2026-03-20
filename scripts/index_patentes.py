"""Comando de consola para construir o actualizar el indice de patentes.

Instrucciones:
- Ejecuta esto antes de usar el agente y cada vez que cambien los PDFs.
- Si `PATENTES_SOURCE_MODE=sharepoint`, primero sincroniza un mirror local.
- Usa las opciones para pruebas rapidas o para acotar el trabajo por sitio.
- Si hay errores, revisar permisos de lectura y la ruta de PATENTES_SOURCE_DIR.
- Errores de extraccion se registran en patentes_agent.index_errors.log.
- La salida es un resumen JSON con totales y tiempos de indexado.
- Se insertan solo dominios validos (AAA999 o AA999AA).
- En modo SharePoint, la salida incluye tambien `sharepoint_sync.telemetry`.
"""

import argparse
import json
import logging

from agent.config import active_source_dir, load_settings
from agent.logging_config import setup_logging
from agent.memory.vector_store import PlateIndex

logger = logging.getLogger(__name__)


def main() -> None:
    """Indexa PDFs y deja estadisticas en consola.

    Flujo:
    - Lee configuracion desde .env y prepara el registro.
    - Si la fuente es SharePoint, sincroniza primero el cache local.
    - Construye o actualiza el indice local en SQLite.
    - Aplica limites opcionales para acelerar pruebas.
    - Imprime un resumen JSON con totales, tiempo total y tiempos por PDF.
    - En modo SharePoint agrega `sharepoint_sync` y su telemetria al resumen final.
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
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Solo sincroniza SharePoint al cache local y no indexa",
    )
    args = parser.parse_args()

    settings = load_settings()
    source_dir = active_source_dir(settings)
    sharepoint_sync = None
    explicit_pdf_paths = None

    if settings.source_mode == "sharepoint":
        from agent.sources.sharepoint_client import SharePointClient

        if args.site:
            logger.warning(
                "La opcion --site se ignora en modo sharepoint; la carpeta se controla con SHAREPOINT_FOLDER_PATH."
            )
        with SharePointClient.from_settings(settings) as client:
            sharepoint_sync = client.sync_folder_to_cache(force=args.force, limit=args.limit)
        if args.sync_only:
            print(json.dumps({"sharepoint_sync": sharepoint_sync}, indent=2))
            return
        source_dir = settings.sharepoint.cache_dir
        if args.limit is not None:
            explicit_pdf_paths = sharepoint_sync.get("local_paths") or None

    index = PlateIndex(settings.index_db, source_dir)
    stats = index.index_source(
        force=args.force,
        limit=None if explicit_pdf_paths is not None else args.limit,
        max_pages_per_pdf=args.max_pages_per_pdf,
        site=args.site if settings.source_mode != "sharepoint" else None,
        log_every=args.log_every,
        pdf_paths=explicit_pdf_paths,
    )
    payload = dict(stats)
    if sharepoint_sync is not None:
        payload["sharepoint_sync"] = sharepoint_sync
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
