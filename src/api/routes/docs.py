"""Ruta para servir PDFs desde la carpeta fuente.

Instrucciones:
- Resolver rutas de forma segura dentro de source_dir.
- Evitar acceso fuera del directorio base.
- Mantener esta ruta sin logica de negocio.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from agent.config import load_settings


router = APIRouter()


def _resolve_safe(base_dir: Path, rel_path: str) -> Path:
    """Resuelve una ruta relativa y valida que quede dentro de base_dir."""
    base = base_dir.resolve()
    candidate = (base / rel_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Documento no encontrado") from exc
    return candidate


@router.get("/docs/{rel_path:path}")
def docs(rel_path: str, settings=Depends(load_settings)) -> FileResponse:
    """Devuelve un PDF ubicado dentro de la carpeta fuente."""
    candidate = _resolve_safe(settings.source_dir, rel_path)
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return FileResponse(candidate)
