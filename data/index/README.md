<!-- NOTA: Documentacion de la carpeta de indice de datos del agente de patentes. -->
# Indice local (patentes.sqlite)

Este directorio almacena el indice SQLite generado por `scripts/index_patentes.py`.
El indice existe para no leer todos los PDFs en cada consulta del agente.
La fuente puede ser local (`PATENTES_SOURCE_DIR`) o un mirror local sincronizado
desde SharePoint (`data/sharepoint_cache`).

## Como se genera `patentes.sqlite`

1. El archivo `scripts/index_patentes.py` recorre los PDFs en la fuente activa.
1. Si `PATENTES_SOURCE_MODE=sharepoint`, primero sincroniza SharePoint a `data/sharepoint_cache`.
1. Extrae texto por pagina con `pypdf`.
1. Prioriza coincidencias etiquetadas como `DOMINIO:`, `PATENTE:`, `MATRICULA:` o `PLACA:` y extrae el primer dominio valido del texto etiquetado.
1. Si no hay etiquetas, usa patrones de respaldo para detectar dominios.
1. Valida formatos de dominio antes de insertar (ej: AAA999 o AA999AA).
1. Guarda todo en SQLite para busqueda rapida.

Trazabilidad de tiempos:
- Cada corrida guarda tiempo total en `index_time_seconds`.
- Cada PDF queda registrado en `pdf_timings[]` con estado, paginas, hits y segundos.
- Los mismos datos se registran en `data/logs/patentes_agent.log`.
- Si la fuente es SharePoint, la salida incluye `sharepoint_sync.telemetry` con requests, descargas y bytes.

Opciones utiles:
- `--force`: reindexa todo aunque no haya cambios.
- `--limit N`: procesa solo N PDFs.
- `--max-pages-per-pdf N`: limita paginas por PDF.
- `--site carpeta`: procesa una subcarpeta dentro de la fuente.

## Como visualizar la base

### Opcion A: DB Browser for SQLite (interfaz grafica)

Abri la aplicacion y selecciona `patentes.sqlite`.

### Opcion B: sqlite3 en consola

```bash
sqlite3 data/index/patentes.sqlite
.tables
.schema
```

### Opcion C: Python rapido

```python
import sqlite3
conn = sqlite3.connect("data/index/patentes.sqlite")
print(conn.execute("select count(*) from plate_hits").fetchone())
```

## Que informacion contiene

- Tabla `documents`: ruta del PDF, mtime, cantidad de paginas indexadas.
- Tabla `pages`: texto por pagina y su version normalizada.
- Tabla `plate_hits`: patente normalizada, forma original encontrada, pagina, extracto y campos de poliza.
- Campos adicionales en `plate_hits`: poliza, certificado, asegurado, vigencia_desde, vigencia_hasta, vehiculo, cobertura, dominio_label.
- Indices: `idx_plate_hits_plate`, `idx_pages_doc`.

Notas:
- `dominio_label` indica si el match vino de `DOMINIO`, `PATENTE`, `MATRICULA` o `PLACA`.
- `label_pages` se deriva agrupando paginas por `dominio_label` (ver `PlateIndex.get_label_pages()`).

## Consejos

- Para reindexar todo: `python scripts/index_patentes.py --force`
- Para validar SharePoint antes del indexado: `python scripts/sharepoint_probe.py --site-info`
- Para medir tiempos: revisar `index_time_seconds` y `pdf_timings` en la salida JSON.
- Para usar un indice alternativo, configura `PATENTES_INDEX_DB`.
- Para ver coincidencias exactas y por subcadena: `python scripts/inspect_db.py --plate ABC123`
- Para ver prefijo o contiene: `python scripts/inspect_db.py --plate AB --mode prefijo`
- Si faltan resultados, revisar la patente o volver a indexar.
- Si cambias la logica de extraccion, siempre reindexa para refrescar el SQLite.
- Errores de extraccion de PDF se registran en `data/logs/patentes_agent.index_errors.log`.
- El modo `fuzzy` busca coincidencias en texto completo y puede dar falsos positivos.
- No editar manualmente la base.
