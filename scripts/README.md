<!-- NOTA: Documentacion de la carpeta scripts del agente de patentes. -->
# Scripts

Esta carpeta contiene utilidades de consola para tareas operativas del proyecto.
No son parte de la API, pero facilitan el mantenimiento y las pruebas locales.

## Archivos

- `index_patentes.py`: genera o actualiza el indice SQLite a partir de los PDFs.
- `chat_cli.py`: inicia un chat por consola para probar el agente sin la API.
- `inspect_db.py`: inspecciona la base SQLite y permite exportar resultados.

## Que acciones realizan

### `index_patentes.py`
- Recorre `PATENTES_SOURCE_DIR`.
- Extrae texto de cada PDF y lo guarda en SQLite.
- Registra coincidencias de patentes y paginas para busqueda rapida.
- Permite limitar el trabajo para pruebas rapidas o por sitio.
- Registra errores de extraccion en `data/logs/patentes_agent.index_errors.log`.
- Registra tiempos por PDF y tiempo total en consola y en `data/logs/patentes_agent.log`.

Opciones principales:
- `--force`: reindexa todos los PDFs aunque no hayan cambiado.
- `--limit N`: procesa solo N PDFs.
- `--max-pages-per-pdf N`: corta el analisis por PDF a N paginas.
- `--site carpeta`: procesa solo una subcarpeta dentro de la fuente.
- `--log-every N`: registra progreso cada N PDFs.
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
```
