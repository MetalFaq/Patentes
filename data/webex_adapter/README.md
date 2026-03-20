<!-- NOTA: Documentacion de la carpeta de persistencia tecnica del adaptador Webex. -->
# Persistencia tecnica del adaptador Webex

Este directorio almacena archivos internos usados por `src/webex_adapter/`.
Su objetivo es sostener la deduplicacion y la trazabilidad tecnica del canal Webex entre reinicios locales.

## Como se genera `webex_events.sqlite`

1. `src/webex_adapter/dedupe.py` crea o abre una base SQLite local.
1. Cada webhook recibido intenta reservar el `message_id` o `event_id`.
1. El adaptador marca eventos en estados como `processing`, `processed` o equivalentes segun el flujo.
1. Si un evento ya estaba registrado, el adaptador evita procesarlo de nuevo.

## Para que existe esta base

- Evitar respuestas duplicadas cuando Webex reintenta el mismo webhook.
- Recordar eventos ya procesados entre reinicios del adaptador.
- Tener una persistencia tecnica minima mientras el adaptador corre en local o en un entorno simple.

## Que informacion contiene

- Identificador del evento o mensaje de Webex.
- Estado tecnico de procesamiento.
- Metadatos minimos del evento.
- Timestamps de registro y actualizacion.

No guarda la conversacion funcional del agente. El historial conversacional vive del lado de `Patentes` y no en esta carpeta.

## Relacion con el resto del proyecto

- `PATENTES_API_BASE_URL` sigue apuntando al backend del agente.
- `webex_events.sqlite` solo evita duplicados del canal Webex.
- Los documentos PDF, el indice `patentes.sqlite` y las sesiones ADK viven en otras carpetas.

## Produccion

- En un entorno productivo, esta persistencia debe vivir en un almacenamiento estable.
- Si el adaptador escala horizontalmente, conviene migrar este store a una alternativa compartida (por ejemplo Redis o una base central).
- No editar manualmente la base.

## Consejos

- Solo se versiona este `README.md`; `webex_events.sqlite` sigue ignorado por git.
- Si queres reiniciar la deduplicacion local desde cero, eliminar la base con el adaptador apagado.
- Para entender el rol completo de este store, ver `src/webex_adapter/README.md` y `doc/LOGS_Y_OBSERVABILIDAD.md`.
- Para comandos utiles de diagnostico del adaptador, ver `doc/COMANDOS_OPERATIVOS_Y_TROUBLESHOOTING.md`.
