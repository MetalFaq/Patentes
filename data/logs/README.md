<!-- NOTA: Documentacion de la carpeta de logs locales y archivos de salida del proyecto. -->
# Logs locales

Este directorio almacena archivos de log generados durante pruebas locales del backend, del adaptador Webex y del tunel publico.
No contiene codigo ni datos funcionales del agente; contiene trazabilidad tecnica para diagnostico.

## Como se generan los archivos

1. `src/agent/logging_config.py` escribe logs funcionales del backend en la ruta configurada para la aplicacion.
1. Al levantar servicios locales con redireccion a archivo, se generan salidas de proceso (`*.local.log`, `*.local.err.log`).
1. Al abrir un tunel publico con `localhost.run`, se pueden guardar sus salidas en `webex_tunnel.out.log` y `webex_tunnel.err.log`.
1. Si un comando no redirige salida a archivo, este directorio puede quedar sin nuevos logs aunque el servicio este corriendo.

## Que archivos suelen aparecer

- `api.local.log`: salida estandar del proceso local de FastAPI/Uvicorn del backend.
- `api.local.err.log`: errores del proceso local del backend.
- `webex_adapter.local.log`: salida estandar del adaptador Webex.
- `webex_adapter.local.err.log`: errores del adaptador Webex.
- `webex_tunnel.out.log`: salida del tunel publico.
- `webex_tunnel.err.log`: errores del tunel publico.
- `localhostrun.out.log` / `localhostrun.err.log`: variantes historicas cuando se uso `localhost.run`.

## Para que sirve esta carpeta

- Confirmar si el backend o el adaptador arrancaron correctamente.
- Ver si llego un `POST /webex/webhook`.
- Identificar errores de arranque, puertos ocupados o cortes del tunel.
- Contrastar problemas de transporte con los logs funcionales centrales del proyecto.

## Relacion con otros logs

- Los logs funcionales principales del backend siguen estando documentados en `doc/LOGS_Y_OBSERVABILIDAD.md`.
- Esta carpeta cubre sobre todo logs de proceso local y soporte de pruebas.
- Los transcripts conversacionales no viven aca; se guardan en `data/conversations.jsonl` y `data/session_store.json` segun corresponda.

## Consejos

- No subir archivos `*.log` al repositorio; solo se versiona este `README.md`.
- Si un log crece demasiado, borrarlo antes de una nueva prueba local.
- Si Webex no responde, revisar primero `webex_adapter.local.err.log` y luego `webex_tunnel.err.log`.
- Si la UI falla, revisar `api.local.err.log`.
- Para una explicacion completa del rol de cada log, ver `doc/LOGS_Y_OBSERVABILIDAD.md`.
