<!-- NOTA: Documentacion de la carpeta scripts del agente de patentes. -->
# Scripts

Esta carpeta contiene utilidades de consola para tareas operativas del proyecto.
No son parte de la API, pero facilitan el mantenimiento y las pruebas locales.

## Archivos

- `index_patentes.py`: genera o actualiza el indice SQLite a partir de los PDFs.
- `chat_cli.py`: inicia un chat por consola para probar el agente sin la API.
- `inspect_db.py`: inspecciona la base SQLite y permite exportar resultados.
- `sharepoint_probe.py`: valida conectividad SharePoint/Graph antes del indexado.
- `sharepoint_scheduler.py`: ejecuta polling incremental SharePoint y dispara indexado solo cuando hace falta.

## Que acciones realizan

### `index_patentes.py`
- Recorre `PATENTES_SOURCE_DIR` o el mirror local de SharePoint segun `PATENTES_SOURCE_MODE`.
- Extrae texto de cada PDF y lo guarda en SQLite.
- Registra coincidencias de patentes y paginas para busqueda rapida.
- Permite limitar el trabajo para pruebas rapidas o por sitio.
- Registra errores de extraccion en `data/logs/patentes_agent.index_errors.log`.
- Registra tiempos por PDF y tiempo total en consola y en `data/logs/patentes_agent.log`.
- En modo SharePoint sincroniza primero la carpeta remota a `data/sharepoint_cache`.
- En modo SharePoint agrega un bloque `sharepoint_sync.telemetry` con requests, descargas y bytes.

Opciones principales:
- `--force`: reindexa todos los PDFs aunque no hayan cambiado.
- `--limit N`: procesa solo N PDFs.
- `--max-pages-per-pdf N`: corta el analisis por PDF a N paginas.
- `--site carpeta`: procesa solo una subcarpeta dentro de la fuente.
- `--log-every N`: registra progreso cada N PDFs.
- `--sync-only`: en modo SharePoint, solo sincroniza y no indexa.
- La salida JSON incluye `index_time_seconds` y `pdf_timings[]` para trazabilidad.

### `chat_cli.py`
- Crea una sesion local del agente.
- Envia mensajes ingresados por consola.
- Imprime la respuesta del agente en pantalla.

### `inspect_db.py`
- Muestra estadisticas de tablas.
- Permite buscar una patente puntual (exacto, prefijo, contiene o fuzzy).
- Exporta resultados a CSV.
- El modo `fuzzy` consulta texto completo y puede arrojar falsos positivos.

Opciones principales:
- `--stats`: muestra conteos por tabla.
- `--plate ABC123`: imprime coincidencias segun el modo.
- `--mode exacto|prefijo|contiene|fuzzy`: define el tipo de busqueda para `--plate`.
- `--export-csv salida.csv`: exporta resultados a CSV (opcionalmente filtrado por patente).
Si no se indica `--mode`, se usa `exacto`.

### `sharepoint_probe.py`
- Resuelve el site configurado por Graph.
- Lista drives/bibliotecas del site.
- Lista hijos inmediatos de la carpeta objetivo.
- Puede listar PDFs recursivos, descargar uno o ejecutar una sync puntual.
- Sirve para validar requests GET antes de tocar el indexado.
- `--sync` devuelve telemetria basica para medir volumen tecnico de cada corrida.

Opciones principales:
- `--site-info`
- `--list-drives`
- `--list-folder`
- `--list-pdfs`
- `--download-one`
- `--sync`
- `--limit N`
- La salida de sync incluye `cache_hit_ratio` y `telemetry.*`.

### `sharepoint_scheduler.py`
- Evalua una franja horaria y dias habiles configurados en `.env`.
- Ejecuta sync incremental sobre SharePoint.
- Reindexa solo PDFs descargados, salvo que haya eliminaciones remotas.
- Usa lock file local para evitar solapamientos entre corridas.
- Persiste estado de slot en `data/sharepoint_cache/.scheduler_state.json`.

Opciones principales:
- `--once`: evalua el slot actual una sola vez y termina.
- `--run-now`: ignora ventana horaria y fuerza una corrida inmediata.
- `--poll-seconds N`: frecuencia de evaluacion en modo continuo.

## Por que son importantes

- Permiten preparar el indice sin necesidad de levantar la API.
- Sirven para depurar el comportamiento del agente rapidamente.
- Evitan dependencias externas durante pruebas basicas.
- Facilitan auditoria y diagnostico del indice.

## Como ejecutar

```powershell
$env:PYTHONPATH=".\src"
python scripts/index_patentes.py
python scripts/chat_cli.py
python scripts/inspect_db.py --stats
python scripts/sharepoint_probe.py --site-info
python scripts/sharepoint_scheduler.py --once
```
