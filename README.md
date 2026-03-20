<!-- NOTA: README del proyecto del agente de patentes. Mantener instrucciones actualizadas. -->
# Agente de Patentes (Google ADK)

Agente IA para buscar informacion de seguro de dominios/patentes en PDFs.
El backend real del agente vive en `src/api` y expone el contrato `POST /chat`.
Webex se integra como canal principal mediante un adaptador separado en
`src/webex_adapter`, mientras que la UI web de `http://localhost:8000/ui`
se mantiene como modo de prueba para desarrollo.

Estado actual de pruebas:
- la UI web local sigue siendo la superficie de prueba confiable
- Webex ya esta integrado a nivel de codigo
- la validacion end-to-end por webhook depende de reachability publica real
- con VPN/proxy corporativo un tunel temporal puede no ser suficiente
- SharePoint queda soportado como fuente via mirror/cache local incremental

## Arquitectura operativa

- Webex user -> Bot Webex
- Bot Webex -> POST /chat en Patentes
- Patentes -> ADK + SQLite + PDFs/SharePoint
- Patentes -> respuesta markdown
- Bot Webex -> mensaje markdown en Webex

## Estructura (resumen)

- `src/agent`: logica del agente, instrucciones, herramientas y memoria
- `src/api`: API FastAPI del backend del agente
- `src/webex_adapter`: adaptador HTTP/Webex basado en webhooks
- `doc`: notas operativas y plan de migracion a produccion
- `scripts`: utilidades (indexado, chat por consola, inspeccion)
- `data/index`: base SQLite generada
- `data/logs`: logs locales y archivos de salida de procesos
- `data/webex_adapter`: persistencia tecnica del adaptador Webex
- `data/sharepoint_cache`: mirror local sincronizado desde SharePoint
- `eval`: casos de prueba

Documentacion ampliada:
- `doc/ARQUITECTURA_GENERAL.md`
- `doc/ENDPOINTS_PUBLICOS_ESTABLES.md`
- `doc/LOGS_Y_OBSERVABILIDAD.md`
- `doc/REQUERIMIENTO_TECNICO_INFRAESTRUCTURA.md`
- `doc/TUNEL_PUBLICO.md`
- `doc/WEBEX_WEBHOOK.md`
- `doc/PRUEBA_END_TO_END.md`
- `doc/MIGRACION_PRODUCCION.md`
- `doc/SHAREPOINT_INTEGRACION.md`
- `doc/SHAREPOINT_OPERACION_Y_COSTOS.md`

## Preparacion del entorno

1. Copia `.env.example` a `.env`.
2. Completa `GOOGLE_API_KEY`.
3. Si vas a usar Webex, completa tambien `WEBEX_BOT_TOKEN` y `WEBEX_WEBHOOK_SECRET`.
4. Si vas a usar SharePoint, completa tambien las variables `SHAREPOINT_*` y `PATENTES_SOURCE_MODE=sharepoint`.
5. Instala el proyecto en modo editable para poder ejecutar `uvicorn api.main:app`
   y `uvicorn webex_adapter.main:app` sin depender de `PYTHONPATH`:

```powershell
python -m pip install -e .
```

Alternativa de diagnostico (no recomendada como configuracion estable):

```powershell
$env:PYTHONPATH=".\src"
```

6. Activa el entorno virtual, por ejemplo:

```powershell
.\venv_patentes_agent\Scripts\Activate.ps1
```

Nota sobre variables de entorno:
- El archivo `.env` se carga automaticamente al iniciar cada servicio.
- Si defines variables en la consola o en el sistema operativo, esas tienen prioridad.
- Para volver a usar lo declarado en `.env`, limpia la variable del entorno o abre una consola nueva.

Ejemplo de limpieza (PowerShell):

```powershell
Remove-Item Env:PATENTES_SOURCE_DIR -ErrorAction SilentlyContinue
Remove-Item Env:PATENTES_INDEX_DB -ErrorAction SilentlyContinue
Remove-Item Env:DOCS_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:WEBEX_BOT_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:WEBEX_WEBHOOK_SECRET -ErrorAction SilentlyContinue
Remove-Item Env:PATENTES_API_BASE_URL -ErrorAction SilentlyContinue
```

## Variables principales

Backend Patentes:
- `GOOGLE_API_KEY`
- `APP_NAME`
- `PATENTES_SOURCE_MODE`
- `PATENTES_SOURCE_DIR`
- `PATENTES_INDEX_DB`
- `PATENTES_SESSION_STORE`
- `PATENTES_TRANSCRIPT_PATH`
- `DOCS_BASE_URL`
- `GEMINI_MODEL`
- `THINKING_LEVEL`

Adaptador Webex:
- `WEBEX_BOT_TOKEN`
- `WEBEX_WEBHOOK_SECRET`
- `WEBEX_API_BASE_URL`
- `WEBEX_REQUEST_TIMEOUT_SECONDS`
- `PATENTES_API_BASE_URL`
- `PATENTES_API_TIMEOUT_SECONDS`
- `WEBEX_DEDUPE_STORE`
- `WEBEX_DEDUPE_TTL_HOURS`
- `WEBEX_ALLOWED_ROOM_TYPES`

SharePoint:
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

## Indexado de PDFs (local)

Ejecuta una vez o cuando cambien los PDFs:

```powershell
python scripts/index_patentes.py
```

Para forzar reindexado:

```powershell
python scripts/index_patentes.py --force
```

Notas del indexado:
- Se priorizan etiquetas `DOMINIO`, `PATENTE`, `MATRICULA` y `PLACA`.
- Solo se insertan dominios validos (formatos `AAA999` o `AA999AA`).
- Errores de extraccion se registran en `data/logs/patentes_agent.index_errors.log`.
- El indexado registra tiempos por PDF y tiempo total en logs y en la salida JSON (`pdf_timings`, `index_time_seconds`).
- Si `PATENTES_SOURCE_MODE=sharepoint`, primero sincroniza SharePoint a `data/sharepoint_cache`.

Medicion de tiempos del indexado:

```powershell
python scripts/index_patentes.py --force
```

La salida JSON incluye:
- `index_time_seconds`: tiempo total del proceso.
- `pdf_timings[]`: detalle por PDF (ruta, estado, paginas, hits y segundos).

Tambien queda trazabilidad en `data/logs/patentes_agent.log` con una linea por PDF y una linea final de resumen.

## SharePoint como fuente

La integracion SharePoint sigue este flujo:

1. autenticacion contra Microsoft Graph con certificado PFX
2. validaciones GET (`site`, `drives`, `children`)
3. descarga incremental a `data/sharepoint_cache`
4. indexado local del mirror/cache

Puntos operativos importantes:
- Microsoft Graph no se mide por "tokens" como una API LLM; conviene mirar requests, descargas, bytes y throttling.
- Cada sync expone `sharepoint_sync.telemetry` con requests Graph, descargas, bytes descargados y reuse del cache.
- La recomendacion actual es polling incremental cada `10 minutos` entre `08:00` y `17:00`.
- `last_modified`/`etag` hacen incremental por polling; si mas adelante se quiere un trigger real, hay que sumar change notifications de Graph y un endpoint publico.
- El proyecto ya incluye `scripts/sharepoint_scheduler.py` para ejecutar ese polling incremental sin solapamientos.

Configuracion minima:

```powershell
$env:PATENTES_SOURCE_MODE="sharepoint"
$env:SHAREPOINT_SITE_URL="https://arcorgroup.sharepoint.com/sites/GC_CORP_InfraestructurayComunicacionesTI"
$env:SHAREPOINT_LIBRARY_NAME="Shared Documents"
$env:SHAREPOINT_FOLDER_PATH="31 - IA y Automatizaciones/Agente Patente (Google)/Fuente de Datos"
```

Smoke tests recomendados:

```powershell
python scripts/sharepoint_probe.py --site-info
python scripts/sharepoint_probe.py --list-drives
python scripts/sharepoint_probe.py --list-folder
python scripts/sharepoint_probe.py --download-one
```

Sincronizacion e indexado:

```powershell
python scripts/index_patentes.py --force
```

Scheduler incremental:

```powershell
python scripts/sharepoint_scheduler.py --once
```

Modo continuo local:

```powershell
python scripts/sharepoint_scheduler.py
```

Documentacion detallada:
- `doc/SHAREPOINT_INTEGRACION.md`
- `doc/SHAREPOINT_OPERACION_Y_COSTOS.md`
- `src/agent/sources/README.md`
- `data/sharepoint_cache/README.md`

Override temporal (solo para esta ejecucion):

```powershell
$env:PATENTES_SOURCE_DIR="<ruta-a-Fuente>"
$env:PATENTES_INDEX_DB=".\data\index\patentes.sqlite"
python scripts/index_patentes.py --force
```

## Ejecutar backend del agente (FastAPI)

```powershell
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Este servicio expone:
- `POST /chat`: contrato estable para clientes (UI, CLI, Webex)
- `POST /chat_debug`: misma respuesta + trazas tecnicas de herramientas
- `GET /docs/{rel_path}`: servicio de PDFs enlazados desde respuestas
- `GET /ui`: UI web de prueba para desarrolladores

### UI web de pruebas

Abri:

```
http://localhost:8000/ui
```

La interfaz usa `/chat_debug` y muestra trazas tecnicas de herramientas.
No expone razonamiento interno del modelo. Se considera superficie de test,
no el canal principal de usuarios.

### Chat por API (manual)

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/chat" `
  -ContentType "application/json" `
  -Body '{"user_id":"test","session_id":"test1","message":"AUT011","channel":"api"}'
```

Para evitar respuestas con contexto previo, cambia el `session_id`:

```powershell
$session = "test_" + (Get-Date -Format "yyyyMMdd_HHmmss")
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/chat" `
  -ContentType "application/json" `
  -Body ("{""user_id"":""test"",""session_id"":""$session"",""message"":""AUT011"",""channel"":""api""}")
```

### Chat por consola

```powershell
python scripts/chat_cli.py
```

## Ejecutar adaptador Webex

El adaptador Webex vive en `src/webex_adapter` y se ejecuta como un servicio
separado. No ejecuta ADK ni consulta SQLite directamente; reenvia cada mensaje a
`POST /chat` del backend de Patentes.

1. Levanta primero el backend de Patentes (`api.main:app`).
2. En otra consola, levanta el adaptador Webex:

```powershell
python -m uvicorn webex_adapter.main:app --host 0.0.0.0 --port 8010 --reload
```

3. Verifica salud local:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8010/webex/health"
```

4. Expone `http://localhost:8010` mediante un tunel HTTPS publico (por ejemplo,
   `cloudflared`, `ngrok`, `localhost.run` o equivalente corporativo).

Ejemplo minimo con `localhost.run`:

```powershell
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes -R 80:localhost:8010 nokey@localhost.run
```

La salida mostrara una URL `https://...` temporal para registrar el webhook.
5. Configura el webhook de Webex apuntando a:

```
https://<tu-url-publica>/webex/webhook
```

Si queres entender por que hace falta un tunel y como funciona una URL publica
temporal, revisa `doc/TUNEL_PUBLICO.md`.
Si queres la teoria y practica del webhook, revisa `doc/WEBEX_WEBHOOK.md`.
Para el circuito completo de prueba, revisa `doc/PRUEBA_END_TO_END.md`.
Ese documento ya consolida en un solo lugar los 10 pasos exactos para correr
una prueba real de Webex end-to-end.
Si la prueba falla por reachability publica, la superficie vigente para validar
el agente sigue siendo `http://localhost:8000/ui` hasta contar con un endpoint
estable o una red sin interferencia sobre el webhook.

Requisitos operativos del adaptador:
- procesa solo eventos `messages.created`
- verifica `X-Spark-Signature` si `WEBEX_WEBHOOK_SECRET` esta configurado
- ignora mensajes del propio bot
- deduplica por `message_id` usando `WEBEX_DEDUPE_STORE`
- responde a Webex usando `markdown`, para preservar links clickeables a PDFs

## Historial de conversacion y sesiones

Fuente de verdad del historial:
- `Patentes` conserva sesiones ADK y transcripciones (`data/conversations.jsonl`).
- `Webex` solo aporta el canal y el identificador del usuario.

Mapeo aplicado por el adaptador Webex:
- `user_id = personId` del mensaje Webex
- `session_id = roomId` para conversaciones directas
- `session_id = roomId:personId` para espacios grupales

El campo opcional `channel` del contrato `/chat` permite registrar si el origen
fue `api`, `ui`, `cli` o `webex` sin cambiar la logica del agente.

## Inspeccion del indice (local)

```powershell
python scripts/inspect_db.py --stats
python scripts/inspect_db.py --plate AUT011
```

Modo prefijo/contiene desde CLI:

```powershell
python scripts/inspect_db.py --plate AUT --mode prefijo
python scripts/inspect_db.py --plate 011 --mode contiene
```

Modo fuzzy (solo para inspeccion manual):

```powershell
python scripts/inspect_db.py --plate AUT011 --mode fuzzy
```

## Seguimiento y diagnostico (sin secretos)

Estas rutas y archivos te permiten verificar el funcionamiento del agente y del canal Webex.

- Registros generales: `data/logs/patentes_agent.log`
- Errores: `data/logs/patentes_agent.error.log`
- Errores de indexado: `data/logs/patentes_agent.index_errors.log`
- Transcripciones de chat (JSONL): `data/conversations.jsonl`
- Sesiones persistidas: `data/session_store.json`
- Dedupe de eventos Webex: `data/webex_adapter/webex_events.sqlite`
- Base del indice: `data/index/patentes.sqlite`

Significado rapido:
- `patentes_agent.log`: actividad general del backend, agente, indexado y adaptador
- `patentes_agent.error.log`: solo errores y excepciones
- `patentes_agent.index_errors.log`: problemas de lectura/indexado de PDFs
- `conversations.jsonl`: transcript funcional, no log tecnico
- `session_store.json`: estado de sesion, no log tecnico
- `webex_events.sqlite`: deduplicacion Webex, no log tecnico

Si queres el detalle completo de cada archivo, revisa `doc/LOGS_Y_OBSERVABILIDAD.md`.

Comandos utiles:

```powershell
Get-Content .\data\logs\patentes_agent.log -Tail 200
Get-Content .\data\logs\patentes_agent.error.log -Tail 200
Get-Content .\data\conversations.jsonl -Tail 20
```

Nota: no compartas ni registres claves de API ni tokens de Webex. Los secretos van en `.env` y no deben subirse a git.

## Ejecucion en Vertex AI / despliegue

En produccion, separa al menos dos servicios:
- backend Patentes (`api.main:app`)
- adaptador Webex (`webex_adapter.main:app`)

El indexado no debe correr al iniciar el backend de chat. Genera el indice en un job previo.

Para el detalle de cambios necesarios al migrar a produccion, revisa:
- `doc/README.md`
- `doc/ENDPOINTS_PUBLICOS_ESTABLES.md`
- `doc/REQUERIMIENTO_TECNICO_INFRAESTRUCTURA.md`
- `doc/MIGRACION_PRODUCCION.md`
- `doc/WEBEX_WEBHOOK.md`

## Notas

- Los enlaces a documentos usan formato `http://<host>/docs/...#page=N`.
- Si no hay resultados, revisa la patente o actualiza el indice.
- En los PDFs, "dominio" es sinonimo de patente.
- Busquedas por prefijo: "listame patentes que empiecen con AUT".
- Busquedas por contiene: "patentes que contengan 011".
- Consultas estadisticas globales solo responden si hubo herramientas.
- El modo `fuzzy` es explicito y puede generar falsos positivos; no se usa por defecto.
- Respuesta estandar: Poliza N°, Vigencia desde, Vigencia hasta, Asegurado y link a la pagina exacta.
