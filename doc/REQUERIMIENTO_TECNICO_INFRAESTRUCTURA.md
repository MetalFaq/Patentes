<!-- NOTA: Documento para Infra/Cloud/Seguridad. Mantener en espanol y sin secretos. -->
# Requerimiento tecnico para Infraestructura

Este documento resume el pedido tecnico necesario para pasar el proyecto
`Patentes` desde un entorno local de desarrollo a un entorno operativo estable.

## 1. Objetivo

Publicar de forma estable dos servicios del proyecto:

1. backend del agente de Patentes
2. adaptador Webex

Con esto se busca:

- eliminar la dependencia de `localhost`
- eliminar la dependencia de tuneles temporales
- permitir la entrega confiable de webhooks desde Webex
- habilitar una operacion sostenida y auditable

## 2. Contexto actual

Hoy el proyecto funciona localmente asi:

- backend: `http://localhost:8000`
- adaptador Webex: `http://localhost:8010`

Para pruebas se utilizo un tunel publico temporal. El resultado fue:

- el bot de Webex existe y puede ver salas/mensajes
- el backend y el adaptador levantan correctamente
- pero la entrega del webhook no fue confiable en entorno corporativo

Conclusión operativa:

- el canal Webex ya esta implementado a nivel de codigo
- lo que falta para volverlo operativo es reachability publica estable

## 3. Alcance del pedido

Se requiere una solucion para exponer con HTTPS estable:

- `api.main:app`
- `webex_adapter.main:app`

No se requiere exponer la UI local de desarrollo como canal principal de negocio.

## 4. Endpoints requeridos

Se necesitan **dos endpoints publicos estables**:

- backend Patentes:
  - `https://patentes-api.<dominio>`
- adaptador Webex:
  - `https://patentes-webex.<dominio>`

Uso previsto:

- Webex webhook:
  - `https://patentes-webex.<dominio>/webex/webhook`
- llamadas internas del adaptador al backend:
  - `https://patentes-api.<dominio>/chat`

## 5. DNS

Se requieren registros DNS para ambos servicios.

Ejemplo:

- `patentes-api.arcor.com`
- `patentes-webex.arcor.com`

Los registros pueden resolverse mediante:

- `A` a IP publica
- `CNAME` a hostname gestionado por la plataforma

segun la arquitectura elegida por Infra.

## 6. HTTPS / certificados

Se requiere:

- TLS valido para ambos endpoints
- certificados administrados por la plataforma o por el equipo de Infra

El webhook de Webex debe consumir HTTPS valido.

## 7. Publicacion / hosting

Se requiere infraestructura para desplegar dos servicios HTTP:

- backend del agente
- adaptador Webex

Alternativas validas:

- VM con reverse proxy
- App Service
- Container Apps
- Cloud Run
- Kubernetes con ingress
- equivalente corporativo

## 8. Red y conectividad

### Ingreso publico

Webex debe poder acceder desde Internet al endpoint:

- `https://patentes-webex.<dominio>/webex/webhook`

### Egreso desde los servicios

El adaptador Webex necesita salida hacia:

- `https://webexapis.com`

El backend del agente necesita salida hacia:

- servicios de Google/Gemini

Si existe proxy corporativo, inspeccion TLS o politica de egress, debe contemplarse
para no bloquear:

- entrega de webhooks
- llamadas del adaptador a Webex
- llamadas del backend a Gemini

## 9. Persistencia requerida

Se requiere persistencia real para:

- indice del agente
- transcript conversacional
- sesiones
- deduplicacion de eventos Webex

Componentes actuales:

- `PATENTES_INDEX_DB`
- `PATENTES_TRANSCRIPT_PATH`
- `PATENTES_SESSION_STORE`
- `WEBEX_DEDUPE_STORE`

Observacion:

- si la solucion escala horizontalmente, no alcanza con archivos efimeros por instancia

## 10. Secretos

Se requiere gestion segura de secretos para:

- `GOOGLE_API_KEY`
- `WEBEX_BOT_TOKEN`
- `WEBEX_WEBHOOK_SECRET`

Opciones esperables:

- Azure Key Vault
- Secret Manager
- runtime secrets de la plataforma

No se recomienda `.env` como mecanismo operativo productivo.

## 11. Configuracion esperada del runtime

Backend:

```env
DOCS_BASE_URL=https://patentes-api.<dominio>
PATENTES_INDEX_DB=<ruta-o-volumen-persistente>
PATENTES_TRANSCRIPT_PATH=<ruta-o-volumen-persistente>
PATENTES_SESSION_STORE=<ruta-o-volumen-persistente>
```

Adaptador:

```env
PATENTES_API_BASE_URL=https://patentes-api.<dominio>
WEBEX_DEDUPE_STORE=<ruta-o-volumen-persistente>
WEBEX_WEBHOOK_SECRET=<secret-manager>
WEBEX_BOT_TOKEN=<secret-manager>
```

## 12. Criterio de aceptacion

La infraestructura se considera lista cuando:

1. ambos endpoints responden por HTTPS
2. Webex puede invocar el webhook estable
3. el adaptador puede llamar a Webex y al backend
4. el backend puede responder a `/chat`
5. los links de documentos funcionan con `DOCS_BASE_URL`
6. transcript, sesiones y dedupe sobreviven reinicios
7. una prueba end-to-end de Webex responde correctamente

## 13. Justificacion tecnica del pedido

Este pedido no busca "mejorar" el agente por codigo, sino resolver una condicion
operativa indispensable:

- el webhook de Webex necesita reachability publica estable

Con tuneles temporales:

- la URL cambia
- la sesion expira
- depende de una notebook encendida
- depende de la red local y de la VPN

Con endpoints estables:

- Webex entrega a una URL fija
- el webhook se configura una sola vez
- el servicio puede operar sin depender del puesto de desarrollo

## 14. Pedido resumido para Infra

Se solicita:

1. publicar dos servicios HTTPS estables:
   - backend Patentes
   - adaptador Webex
2. asignar DNS para ambos
3. proveer certificados TLS validos
4. habilitar salida de red a Webex y Gemini
5. proveer persistencia para indice, sesiones, transcript y dedupe
6. proveer gestion segura de secretos

## 15. Documentacion relacionada

- `doc/ENDPOINTS_PUBLICOS_ESTABLES.md`
- `doc/MIGRACION_PRODUCCION.md`
- `doc/WEBEX_WEBHOOK.md`
- `doc/TUNEL_PUBLICO.md`
- `doc/PRUEBA_END_TO_END.md`
