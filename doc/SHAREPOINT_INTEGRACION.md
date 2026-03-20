<!-- NOTA: Guia de integracion SharePoint/Graph para el agente de patentes. -->
# Integracion SharePoint

Este documento describe la arquitectura, configuracion y pruebas por etapas para
usar SharePoint como fuente de PDFs del agente de patentes.

## Objetivo

El proyecto no indexa PDFs directamente desde SharePoint en cada consulta.
El flujo adoptado es:

1. autenticarse contra Microsoft Graph
2. listar PDFs de una carpeta SharePoint
3. descargarlos a un mirror/cache local
4. indexar ese mirror con el indexador actual
5. optimizar incrementalmente por `etag` y `lastModified`

Esta estrategia reduce riesgo, reutiliza el indice SQLite existente y permite
depurar conectividad remota antes de mezclarla con el motor de busqueda.

## Datos actuales del proyecto

- Site URL:
  - `https://arcorgroup.sharepoint.com/sites/GC_CORP_InfraestructurayComunicacionesTI`
- Biblioteca objetivo:
  - `Shared Documents`
- Carpeta objetivo:
  - `31 - IA y Automatizaciones/Agente Patente (Google)/Fuente de Datos`
- Modo de autenticacion elegido:
  - certificado PFX local para entorno de desarrollo

## Arquitectura

```mermaid
flowchart LR
    A[SharePoint folder] --> B[Microsoft Graph]
    B --> C[scripts/sharepoint_probe.py]
    B --> D[sync SharePoint -> data/sharepoint_cache]
    D --> E[scripts/index_patentes.py]
    E --> F[data/index/patentes.sqlite]
    F --> G[POST /chat]
    G --> H[/docs/... sirve PDFs desde cache]
```

## Configuracion necesaria

Variables nuevas o relevantes:

- `PATENTES_SOURCE_MODE=sharepoint`
- `SHAREPOINT_TENANT_ID`
- `SHAREPOINT_CLIENT_ID`
- `SHAREPOINT_SITE_URL`
- `SHAREPOINT_LIBRARY_NAME`
- `SHAREPOINT_FOLDER_PATH`
- `SHAREPOINT_CERT_THUMBPRINT`
- `SHAREPOINT_CERT_PFX_PATH`
- `SHAREPOINT_CERT_PFX_PASSWORD`
- `SHAREPOINT_CACHE_DIR`
- `SHAREPOINT_REQUEST_TIMEOUT_SECONDS`
- `SHAREPOINT_GRAPH_BASE_URL`
- `SHAREPOINT_SYNC_INTERVAL_MINUTES`
- `SHAREPOINT_SYNC_WINDOW_START`
- `SHAREPOINT_SYNC_WINDOW_END`
- `SHAREPOINT_SYNC_WEEKDAYS`

## Certificado: desarrollo vs produccion

### Desarrollo actual

Se usa `PFX path directo` por simplicidad:
- el archivo `.pfx` vive fuera de git
- la passphrase se carga por `.env`
- el cliente Graph usa `msal` con `private_key_pfx_path`

### Camino a produccion

Queda anotado como mejora:
- mover la clave privada a un vault/secret store
- evitar distribuir el `.pfx` como archivo local
- evaluar PEM + thumbprint o recuperacion desde Key Vault/Secret Manager

La decision de produccion no cambia la arquitectura de sync/cache local.

## Frecuencia recomendada

Recomendacion operativa acordada:

- sync incremental cada `10 minutos`
- ventana laboral `08:00` a `17:00`
- dias habiles
- ejecucion manual disponible para soporte

Condiciones:
- el job no debe solaparse
- si una corrida sigue activa, la siguiente debe esperar o cancelarse

Para detalle operativo de costos tecnicos, requests y bytes:
- `doc/SHAREPOINT_OPERACION_Y_COSTOS.md`

El proyecto ya incluye un scheduler local:

```powershell
python scripts/sharepoint_scheduler.py --once
```

## Smoke tests por etapas

Primero validar solo GETs, sin indexar:

```powershell
python scripts/sharepoint_probe.py --site-info
python scripts/sharepoint_probe.py --list-drives
python scripts/sharepoint_probe.py --list-folder
python scripts/sharepoint_probe.py --list-pdfs --limit 5
```

Luego validar descarga:

```powershell
python scripts/sharepoint_probe.py --download-one
```

Finalmente sync completo o incremental:

```powershell
python scripts/sharepoint_probe.py --sync
python scripts/index_patentes.py --force
```

La salida JSON del sync incluye:
- `cache_hit_ratio`
- `telemetry.graph_requests_total`
- `telemetry.graph_download_requests`
- `telemetry.bytes_downloaded_mb`
- `telemetry.throttled_responses`

## Flujo incremental

El mirror local usa un manifest tecnico en `data/sharepoint_cache/.manifest.json`.

Por archivo se conserva:
- `item_id`
- `relative_path`
- `etag`
- `last_modified`
- `size`
- `web_url`

Reglas:
- si `etag` o `last_modified` cambian, se vuelve a descargar
- si no cambian, se omite la descarga
- si el archivo desaparece en SharePoint, se elimina del cache en sync completa
- el indexador luego hace prune de documentos ausentes al recorrer la fuente completa

Importante:
- esto es incremental por polling
- no es un trigger nativo de SharePoint
- un trigger real requeriria change notifications + endpoint publico + reconciliacion incremental

## Requests Graph esperados

1. Resolver site:
   - `GET /sites/{hostname}:/{site-relative-path}`
2. Listar bibliotecas:
   - `GET /sites/{site-id}/drives`
3. Listar hijos de carpeta:
   - `GET /drives/{drive-id}/root:/{folder-path}:/children`
4. Descargar contenido:
   - `GET /drives/{drive-id}/items/{item-id}/content`

## Riesgos a vigilar

- permisos Graph insuficientes
- nombre visible de biblioteca distinto al nombre real del drive
- path de carpeta mal codificado
- certificados vencidos o PFX no accesible
- cache local no persistente en produccion
- jobs superpuestos
- proxy corporativo o salida restringida hacia Graph
- throttling (`429`) por exceso de frecuencia o volumen
- `pypdf` puede arrojar `MemoryError` en paginas especialmente pesadas; hoy se registra el warning y el indexado continua

## Archivos involucrados

- `src/agent/config.py`
- `src/agent/sources/sharepoint_client.py`
- `scripts/sharepoint_probe.py`
- `scripts/index_patentes.py`
- `src/api/routes/docs.py`
- `data/sharepoint_cache/README.md`

## Fuentes oficiales

- MSAL Python client credentials con certificados:
  - https://learn.microsoft.com/en-us/entra/msal/python/advanced/client-credentials
- `ConfidentialClientApplication` en MSAL Python:
  - https://learn.microsoft.com/en-us/python/api/msal/msal.application.confidentialclientapplication?view=msal-py-latest
- Microsoft Graph SharePoint resources:
  - https://learn.microsoft.com/en-us/graph/api/resources/sharepoint?view=graph-rest-1.0
- Microsoft Graph list drives:
  - https://learn.microsoft.com/en-us/graph/api/drive-list?view=graph-rest-1.0
- Microsoft Graph list children:
  - https://learn.microsoft.com/en-us/graph/api/driveitem-list-children?view=graph-rest-1.0
- Microsoft Graph download content:
  - https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0
- Microsoft Graph change notifications:
  - https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks
- Microsoft Graph drive delta:
  - https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0

## Decision actual

La integracion SharePoint queda implementada y validada para:
- autenticacion PFX en desarrollo
- validacion por requests GET
- mirror/cache local
- sync incremental por metadatos
- indexado local reutilizando SQLite actual
- servicio de PDFs desde el cache local en modo SharePoint

Validacion real ya ejecutada sobre el site configurado:
- resolucion de site: OK
- listado de drives: OK
- resolucion de biblioteca por alias `Shared Documents` -> `Documents`: OK
- listado de carpeta objetivo: OK
- descarga de un PDF al cache: OK
- sync completo: `17` PDFs
- reindexado final: `17` documentos, `2638` paginas, `833` plate hits

El siguiente paso tecnico recomendado ya no es la conectividad basica, sino:
- operar el mirror con frecuencia programada
- consolidar monitoreo/alertas
- evaluar mas adelante change notifications si negocio necesita menor latencia
