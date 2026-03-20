"""Smoke tests por consola para validar SharePoint antes del indexado.

Instrucciones:
- Usa este script para validar conectividad Graph por etapas.
- Primero proba GETs (`--site-info`, `--list-drives`, `--list-folder`).
- Recién después usa `--download-one` o `--sync`.
- No imprime secretos ni tokens.
- `--sync` devuelve tambien telemetria basica de requests, bytes y cache hits.
"""

import argparse
import json

from agent.config import load_settings
from agent.logging_config import setup_logging
from agent.sources.sharepoint_client import SharePointClient


def main() -> None:
    """Ejecuta chequeos puntuales de SharePoint y devuelve JSON en consola.

    Este script sirve para separar problemas de configuracion/autenticacion Graph
    de problemas del indexador. Cuando se usa `--sync`, el JSON incluye resumen
    de descarga y telemetria operativa de la corrida.
    """
    setup_logging()
    parser = argparse.ArgumentParser(description="Valida integracion SharePoint/Graph")
    parser.add_argument("--site-info", action="store_true", help="Resuelve el site configurado")
    parser.add_argument("--list-drives", action="store_true", help="Lista bibliotecas del site")
    parser.add_argument(
        "--list-folder",
        action="store_true",
        help="Lista hijos inmediatos de la carpeta configurada",
    )
    parser.add_argument(
        "--list-pdfs",
        action="store_true",
        help="Lista PDFs recursivos dentro de la carpeta objetivo",
    )
    parser.add_argument(
        "--download-one",
        action="store_true",
        help="Descarga el primer PDF encontrado al cache local",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sincroniza la carpeta configurada hacia el cache local",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limita cantidad de items")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fuerza descarga aunque el archivo no haya cambiado",
    )
    args = parser.parse_args()

    if not any(
        [
            args.site_info,
            args.list_drives,
            args.list_folder,
            args.list_pdfs,
            args.download_one,
            args.sync,
        ]
    ):
        args.site_info = True
        args.list_drives = True
        args.list_folder = True

    settings = load_settings()
    with SharePointClient.from_settings(settings) as client:
        payload: dict[str, object] = {
            "source_mode": settings.source_mode,
            "cache_dir": str(settings.sharepoint.cache_dir),
        }

        if args.site_info:
            payload["site_info"] = client.get_site_info().__dict__
        if args.list_drives:
            payload["drives"] = [drive.__dict__ for drive in client.list_drives()]
        if args.list_folder:
            payload["folder_children"] = client.list_folder_children()
        if args.list_pdfs:
            payload["pdfs"] = [item.__dict__ for item in client.iter_folder_pdfs(limit=args.limit)]
        if args.download_one:
            first = next(client.iter_folder_pdfs(limit=1), None)
            if first is None:
                payload["download_one"] = {"found": False}
            else:
                local_path = client._safe_local_path(settings.sharepoint.cache_dir, first.relative_path)
                client.download_file(first, local_path)
                payload["download_one"] = {
                    "found": True,
                    "item": first.__dict__,
                    "local_path": str(local_path),
                }
        if args.sync:
            payload["sync"] = client.sync_folder_to_cache(force=args.force, limit=args.limit)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
