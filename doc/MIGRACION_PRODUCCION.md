<!-- NOTA: Guia de migracion a produccion. Mantener en espanol y sin secretos. -->
# Migracion a produccion

## Estado actual

En desarrollo local el proyecto funciona asi:

- backend Patentes: `http://localhost:8000`
- adaptador Webex: `http://localhost:8010`
- Webex no puede llamar directamente a `localhost`, por lo que para pruebas hace falta un tunel HTTPS o un despliegue publico.

## Que cambia en produccion

Hay que sacar al proyecto de `localhost` en dos frentes:

1. **Backend del agente**
   - hoy: `http://localhost:8000`
   - produccion: `https://<backend-patentes>`
   - variable afectada: `PATENTES_API_BASE_URL`
   - variable afectada: `DOCS_BASE_URL`

2. **Adaptador Webex**
   - hoy: `http://localhost:8010`
   - produccion: `https://<webex-adapter>`
   - webhook real: `https://<webex-adapter>/webex/webhook`

## DNS y publicacion

### Prueba local

No conviene crear un registro DNS `A` apuntando a una IP local o privada.
Para pruebas, lo correcto es exponer el adaptador con un tunel HTTPS:

- `cloudflared`
- `ngrok`
- `localhost.run`
- equivalente corporativo

La URL publica generada por ese tunel se usa como `targetUrl` del webhook.

### Produccion

Si se publica con dominio propio:

- un registro `A` apunta a la IP publica del balanceador/reverse proxy/VM/ingress
- un registro `CNAME` apunta al hostname gestionado por la plataforma si corresponde

El DNS **no** debe apuntar a la IP local de la notebook ni a una IP privada de LAN,
salvo que exista NAT, apertura de puertos, TLS y una operacion sostenida, cosa que no es recomendable.

## Variables que dejan de usar localhost

### Backend Patentes

En produccion:

```env
DOCS_BASE_URL=https://patentes-backend.midominio.com
```

### Adaptador Webex

Si el adaptador accede al backend por URL publica:

```env
PATENTES_API_BASE_URL=https://patentes-backend.midominio.com
```

Si ambos servicios corren dentro de la misma red privada, `PATENTES_API_BASE_URL`
puede ser una URL interna del cluster o balanceador interno.

## Secretos

En produccion no conviene usar `.env` como fuente principal. Mover a:

- Secret Manager
- Azure Key Vault
- variables seguras del runtime

Secretos minimos:

- `GOOGLE_API_KEY`
- `WEBEX_BOT_TOKEN`
- `WEBEX_WEBHOOK_SECRET`
- credenciales SharePoint (`client_id`, certificado y passphrase)

Para SharePoint en produccion:
- no conviene distribuir el `.pfx` como archivo local dentro del deployment
- conviene mover certificado y passphrase a `Key Vault` o secret store equivalente
- queda abierto evaluar `PEM + thumbprint` o carga del PFX desde vault, segun la plataforma

## Persistencia que hoy es local

### `WEBEX_DEDUPE_STORE`

Hoy:

```env
WEBEX_DEDUPE_STORE=./data/webex_adapter/webex_events.sqlite
```

Esto sirve en local. En produccion hay tres opciones razonables:

1. volumen persistente compartido
2. SQLite persistido en disco estable del servicio
3. mover dedupe a Redis o base centralizada

Si el servicio escala horizontalmente, un SQLite local por instancia ya no alcanza para deduplicar globalmente.

### Sesiones y transcript

Tambien hay que revisar:

- `PATENTES_SESSION_STORE`
- `PATENTES_TRANSCRIPT_PATH`

Si las instancias reinician o escalan, esos archivos locales no garantizan continuidad.

### Mirror SharePoint

Tambien hay que decidir:

- si `data/sharepoint_cache` vive en volumen persistente
- si el scheduler corre dentro del mismo servicio o como job separado
- si el sync incremental se dispara por polling programado o, mas adelante, por change notifications de Graph

En la etapa actual, el camino recomendado sigue siendo polling incremental mas reconciliacion diaria.

## Topologia recomendada

Separar dos servicios:

1. `api.main:app`
2. `webex_adapter.main:app`

Flujo:

- Webex -> adaptador
- adaptador -> backend Patentes
- backend Patentes -> ADK + indice + documentos

## Checklist de salida a produccion

- [ ] backend Patentes publicado con HTTPS
- [ ] adaptador Webex publicado con HTTPS
- [ ] tunel temporal reemplazado por URL publica estable
- [ ] `DOCS_BASE_URL` actualizado
- [ ] `PATENTES_API_BASE_URL` actualizado
- [ ] webhook de Webex creado con la URL publica real
- [ ] `WEBEX_WEBHOOK_SECRET` cargado en el runtime
- [ ] credenciales SharePoint movidas a vault/secret store
- [ ] scheduler de mirror SharePoint definido (cada 10 min, sin solapamiento)
- [ ] alertas de throttling o corrida larga para SharePoint
- [ ] `WEBEX_DEDUPE_STORE` persistente o reemplazado
- [ ] sesiones/transcripts revisados para persistencia real
- [ ] logs centralizados
- [ ] prueba end-to-end de mensaje en Webex

## Documentos relacionados

- `doc/ENDPOINTS_PUBLICOS_ESTABLES.md`
- `doc/ARQUITECTURA_GENERAL.md`
- `doc/TUNEL_PUBLICO.md`
- `doc/WEBEX_WEBHOOK.md`
- `doc/PRUEBA_END_TO_END.md`
