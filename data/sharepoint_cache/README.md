<!-- NOTA: Documentacion del mirror local sincronizado desde SharePoint. -->
# Mirror local de SharePoint

Esta carpeta recibe el contenido descargado desde SharePoint cuando
`PATENTES_SOURCE_MODE=sharepoint`.
Su objetivo es desacoplar la descarga remota del indexado local.

## Que se guarda aca

- PDFs descargados desde la carpeta objetivo de SharePoint.
- Un manifest local interno (`.manifest.json`) con metadatos tecnicos
  como `item_id`, `etag`, `last_modified` y ruta relativa.
- El manifest no guarda secretos ni tokens.

## Para que existe

- Reusar el indexador SQLite actual sin depender de lectura remota directa.
- Evitar descargar de nuevo archivos que no cambiaron.
- Servir documentos via `/docs/...` cuando el backend opera en modo SharePoint.

## Reglas

- No subir PDFs ni el manifest al repositorio.
- Solo se versiona este `README.md`.
- Si se borra esta carpeta, la siguiente sincronizacion completa volvera a bajarla.

## Flujo

1. `scripts/sharepoint_probe.py` valida conectividad Graph.
2. `scripts/index_patentes.py` sincroniza SharePoint a esta carpeta.
3. `PlateIndex` indexa el mirror local.
4. La API sirve PDFs desde esta misma carpeta cuando corresponde.

## Operacion

- La frecuencia recomendada del mirror es cada `10 minutos` en horario laboral.
- La deteccion por `etag`/`last_modified` evita redescargas innecesarias.
- El scheduler incremental guarda un estado tecnico en `.scheduler_state.json` para no repetir la misma corrida dentro del mismo slot.
- Un trigger real por cambios futuros requeriria change notifications de Graph; este mirror actual funciona por polling incremental.
