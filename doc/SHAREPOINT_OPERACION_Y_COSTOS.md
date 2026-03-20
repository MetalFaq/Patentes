<!-- NOTA: Guia operativa SharePoint sobre frecuencia, monitoreo y costos. -->
# SharePoint: operacion, monitoreo y costos

Este documento baja a tierra como operar la sincronizacion SharePoint del
proyecto y como medir su impacto tecnico. El foco no es facturacion LLM sino
volumen real de requests, bytes descargados, latencia y throttling.

## Aclaracion sobre "tokens" y costos

La autenticacion actual a Microsoft Graph usa:

- App Registration
- certificado PFX
- token app-only emitido por Entra ID

Ese token no funciona como los tokens de una API LLM. En esta integracion no se
monitorea costo por token consumido. Lo que realmente conviene medir es:

- cantidad de requests a Graph
- cantidad de descargas de archivos
- bytes descargados
- tiempo total de sync
- porcentaje de reuse del cache (`cache_hit_ratio`)
- cantidad de respuestas `429` o throttling

## Telemetria que ya expone el proyecto

Cada `sync` devuelve en JSON y registra en logs:

- `files_found`
- `downloaded`
- `skipped`
- `deleted`
- `sync_time_seconds`
- `cache_hit_ratio`
- `telemetry.token_acquisitions`
- `telemetry.graph_json_requests`
- `telemetry.graph_download_requests`
- `telemetry.graph_requests_total`
- `telemetry.bytes_downloaded`
- `telemetry.bytes_downloaded_mb`
- `telemetry.throttled_responses`
- `telemetry.status_codes`

Esto aparece en:

- salida de `scripts/sharepoint_probe.py --sync`
- bloque `sharepoint_sync` de `scripts/index_patentes.py`
- `data/logs/patentes_agent.log`

## Como leer esos indicadores

### `graph_requests_total`

Sirve para medir volumen de llamadas a Graph por corrida.

Interpretacion:
- si sube mucho y `downloaded` no acompaña, conviene revisar frecuencia o path
- si se mantiene estable y `downloaded` baja, el incremental esta funcionando

### `graph_download_requests`

Cuenta solo descargas reales de contenido PDF.

Interpretacion:
- cada descarga equivale a un archivo bajado desde SharePoint
- este numero tiene correlacion directa con ancho de banda y tiempo total

### `bytes_downloaded_mb`

Sirve para dimensionar transferencia real por corrida.

Interpretacion:
- si el valor diario es alto, conviene espaciar syncs o afinar incremental
- si es bajo y `cache_hit_ratio` es alto, el mirror esta sano

### `cache_hit_ratio`

Mide que fraccion de archivos no requirio descarga.

Interpretacion:
- alto: buen reuse del cache
- bajo: hubo muchos cambios reales o se esta forzando demasiado el sync

### `throttled_responses`

Cuenta respuestas `429`.

Interpretacion:
- ideal: `0`
- si aparece con frecuencia, el problema ya no es costo sino presion sobre Graph

## Frecuencia recomendada

Para el escenario actual:

- sync incremental cada `10 minutos`
- solo de `08:00` a `17:00`
- dias habiles
- sync manual habilitado para soporte/desarrollo

Razon:
- el incremental por `etag` / `last_modified` reduce descarga innecesaria
- `10 minutos` equilibra frescura y carga
- cada corrida actual ya recorre el arbol remoto completo y reconcilia eliminaciones

## Regla operativa critica

El job no debe solaparse.

Si una corrida sigue viva:
- la siguiente no debe arrancar
- o debe cancelarse de forma explicita

Sin esta regla, el mirror y el indice pueden competir por disco, CPU y ancho de
banda, y la telemetria deja de ser interpretable.

## Scheduler implementado en el proyecto

El proyecto ya incluye:

- `scripts/sharepoint_scheduler.py`

Ese script:
- evalua la ventana laboral configurada
- evita repetir el mismo slot
- usa lock file local para no solaparse
- corre sync incremental
- indexa solo si hubo cambios remotos

Variables asociadas:
- `SHAREPOINT_SYNC_INTERVAL_MINUTES`
- `SHAREPOINT_SYNC_WINDOW_START`
- `SHAREPOINT_SYNC_WINDOW_END`
- `SHAREPOINT_SYNC_WEEKDAYS`

Ejemplos:

```powershell
python scripts/sharepoint_scheduler.py --once
python scripts/sharepoint_scheduler.py --run-now
python scripts/sharepoint_scheduler.py
```

## Trigger real vs incremental por polling

`last_modified` o `etag` no son un trigger. Son una forma de incremental por
polling.

Hoy el proyecto hace esto:

1. consulta Graph
2. compara metadatos (`etag`, `last_modified`, `size`)
3. descarga solo lo que cambio

Eso es correcto y suficiente para esta etapa, pero sigue siendo polling.

## Si se quiere "solo cuando hay cambios"

Para eso hace falta un flujo distinto:

1. crear una suscripcion de Microsoft Graph (change notification)
2. exponer un endpoint publico HTTPS para recibir la notificacion
3. al recibirla, ejecutar delta query o sync incremental

En otras palabras:
- webhook de Graph = avisa que hubo cambio
- delta query / incremental = determina que cambio realmente

El webhook solo no reemplaza la reconciliacion.

## Recomendacion tecnica

Fase actual recomendada:
- mantener polling incremental programado

Fase posterior, si negocio lo justifica:
- agregar change notifications de Graph
- seguir usando incremental/delta para consolidar estado

No conviene saltar directo a un esquema 100% event-driven sin tener primero el
mirror incremental estable y observado.

## Produccion

Para produccion, ademas de la frecuencia y telemetria, conviene ajustar:

- certificado fuera de archivo local (`Key Vault` / secret store)
- logs centralizados
- almacenamiento persistente del mirror si se requiere continuidad
- scheduler centralizado o job runner
- alertas si `throttled_responses > 0`
- alertas si `sync_time_seconds` supera el intervalo programado

## Fuentes oficiales

- MSAL Python client credentials con certificados:
  - https://learn.microsoft.com/en-us/entra/msal/python/advanced/client-credentials
- Microsoft Graph change notifications:
  - https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks
- Microsoft Graph subscriptions:
  - https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0
- Microsoft Graph delta query para drive items:
  - https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0
