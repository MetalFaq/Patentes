<!-- NOTA: Documentacion del adaptador Webex. Mantener en espanol y sin secretos. -->
# Carpeta `src/webex_adapter`

Esta carpeta implementa el canal Webex del proyecto `Patentes`.
No contiene logica del agente ni acceso directo al indice SQLite. Su unica
responsabilidad es transportar mensajes entre Webex y el backend `POST /chat`.

Estado operativo actual:
- el adaptador esta implementado y puede levantarse localmente
- el backend responde correctamente a `/chat`
- las pruebas end-to-end con Webex dependen de que el webhook llegue al endpoint publico
- si la red corporativa o la VPN interfieren con el tunel, la UI local sigue siendo el canal de prueba vigente

Para teoria operativa mas amplia ver:

- `doc/ARQUITECTURA_GENERAL.md`
- `doc/LOGS_Y_OBSERVABILIDAD.md`
- `doc/TUNEL_PUBLICO.md`
- `doc/WEBEX_WEBHOOK.md`
- `doc/PRUEBA_END_TO_END.md`

Arquitectura objetivo:

- Webex user -> Bot Webex
- Bot Webex -> POST /chat en Patentes
- Patentes -> ADK + SQLite + PDFs/SharePoint
- Patentes -> respuesta markdown
- Bot Webex -> mensaje markdown en Webex

## Como se compone

- `__init__.py`: descripcion del paquete.
- `config.py`: carga y valida configuracion del adaptador.
- `schemas.py`: modelos Pydantic del webhook y de la llamada a Patentes.
- `client.py`: clientes HTTP para Webex y Patentes.
- `dedupe.py`: deduplicacion persistente con SQLite.
- `service.py`: flujo completo de procesamiento del mensaje.
- `webhook_handler.py`: validacion del webhook y de la firma HMAC.
- `main.py`: app FastAPI del adaptador.

## Flujo de un mensaje

1. Webex envia un webhook `messages.created` a `POST /webex/webhook`.
2. `webhook_handler.py` valida la firma `X-Spark-Signature` si hay secreto configurado.
3. `service.py` deduplica por `message_id` usando `WEBEX_DEDUPE_STORE`.
4. `client.py` recupera el detalle del mensaje con `GET /messages/{id}`.
5. El adaptador ignora mensajes del propio bot, mensajes vacios y tipos de sala no permitidos.
6. El adaptador construye `user_id` y `session_id` para `POST /chat`.
7. El backend Patentes responde texto/markdown.
8. El adaptador publica la respuesta de vuelta en Webex usando el campo `markdown`.

## Historial y sesiones

Fuente de verdad:
- `Patentes` conserva sesiones y transcripciones.
- `src/webex_adapter` solo conserva dedupe y logs tecnicos.

Mapeo de identidad:
- `user_id = personId`
- `session_id = roomId` para mensajes directos
- `session_id = roomId:personId` para espacios grupales

## Variables de entorno

Obligatorias:
- `WEBEX_BOT_TOKEN`
- `PATENTES_API_BASE_URL`

Recomendadas:
- `WEBEX_WEBHOOK_SECRET`
- `WEBEX_DEDUPE_STORE`
- `WEBEX_ALLOWED_ROOM_TYPES`

Opcionales con defaults:
- `WEBEX_API_BASE_URL=https://webexapis.com/v1`
- `WEBEX_REQUEST_TIMEOUT_SECONDS=30`
- `PATENTES_API_TIMEOUT_SECONDS=60`
- `WEBEX_DEDUPE_TTL_HOURS=72`

## Ejecucion local

1. Levanta primero el backend de Patentes:

```powershell
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

2. En otra consola, levanta el adaptador Webex:

```powershell
python -m uvicorn webex_adapter.main:app --host 0.0.0.0 --port 8010 --reload
```

3. Verifica salud:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8010/webex/health"
```

4. Expone el puerto 8010 con un tunel HTTPS publico.

Ejemplo rapido con `localhost.run` usando el cliente `ssh` de Windows:

```powershell
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes -R 80:localhost:8010 nokey@localhost.run
```

La salida mostrara una URL publica `https://...` que debes usar como base del webhook.
Ese tunel es temporal: si el proceso `ssh` termina, la URL deja de servir.
La teoria detallada de este mecanismo esta en `doc/TUNEL_PUBLICO.md`.

5. Registra en Webex el webhook apuntando a `https://<url>/webex/webhook`.

Ejemplo por API reutilizando los valores de `.env`:

```powershell
$token = (Get-Content .env | Where-Object { $_ -match '^WEBEX_BOT_TOKEN=' } | ForEach-Object { ($_ -split '=', 2)[1] })
$secret = (Get-Content .env | Where-Object { $_ -match '^WEBEX_WEBHOOK_SECRET=' } | ForEach-Object { ($_ -split '=', 2)[1] })
$targetUrl = "https://<url-publica>/webex/webhook"

$body = @{
  name = "patentes-webhook"
  targetUrl = $targetUrl
  resource = "messages"
  event = "created"
  secret = $secret
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "https://webexapis.com/v1/webhooks" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body $body
```

El detalle teorico y operativo del webhook esta en `doc/WEBEX_WEBHOOK.md`.

## Rol de `WEBEX_DEDUPE_STORE`

`WEBEX_DEDUPE_STORE` apunta a un SQLite local usado por `dedupe.py`.
Su funcion es:
- evitar responder dos veces al mismo `message_id`
- recordar eventos ya procesados entre reinicios del adaptador
- marcar eventos en curso (`processing`) para ignorar reintentos simultaneos
- liberar el lock si el procesamiento falla y Webex necesita reintentar

Por defecto:

```text
data/webex_adapter/webex_events.sqlite
```

En desarrollo alcanza con un archivo local. En produccion debe vivir en un volumen
persistente o reemplazarse por una persistencia compartida.

## Riesgos y mitigaciones implementadas

- Mensajes duplicados: `dedupe.py` mantiene estado persistente por `message_id`.
- Loops del bot: se ignoran mensajes cuyo autor sea el propio bot.
- Reintentos del webhook mientras un mensaje sigue en curso: se usa estado `processing` con timeout de obsolescencia.
- Perdida de links: la respuesta a Webex se publica con `markdown`, no con `text`.
- Tipos de sala no deseados: `WEBEX_ALLOWED_ROOM_TYPES` limita direct/group segun despliegue.

Riesgo residual a vigilar:
- Si el backend Patentes tarda demasiado o falla despues de reservar el evento, Webex puede reintentar. El adaptador libera la reserva cuando ocurre un error, pero durante la ventana de procesamiento puede haber reintentos ignorados como `duplicate_or_in_progress`.
- Si Webex ve el bot y el bot ve la sala pero nunca entra `POST /webex/webhook`, el problema suele estar en la reachability publica del endpoint (tunel, VPN, proxy o WAF), no en la logica del adaptador.

## Logs y diagnostico

- Log principal: `data/logs/patentes_agent.log`
- Errores: `data/logs/patentes_agent.error.log`
- Dedupe store: `data/webex_adapter/webex_events.sqlite`
- Logs opcionales de proceso local: `data/logs/webex_adapter.local.log` y `data/logs/webex_adapter.local.err.log`
- Logs opcionales del tunel: `data/logs/webex_tunnel.out.log` y `data/logs/webex_tunnel.err.log`

Eventos tipicos de log:
- llamadas salientes a Webex (`GET /messages/{id}`, `POST /messages`)
- llamadas a `POST /chat`
- eventos ignorados por dedupe, self-message o tipo de sala
- arranque del adaptador con backend configurado y ruta del store

El detalle completo de que genera cada archivo, para que existe y cuando
consultarlo esta en `doc/LOGS_Y_OBSERVABILIDAD.md`.

## Buenas practicas

- No incrustes tokens de Webex en el codigo.
- No mezcles logica del agente dentro del adaptador.
- Mantene el webhook con HTTPS y secreto activo.
- Usa `WEBEX_ALLOWED_ROOM_TYPES=direct` si queres arrancar con un alcance mas controlado.
- Para despliegue y DNS, revisa `doc/MIGRACION_PRODUCCION.md`.
