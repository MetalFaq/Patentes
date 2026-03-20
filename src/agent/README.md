<!-- NOTA: Documentacion de src/agent. Mantener esta guia en espanol y sin secretos. -->
# Carpeta `src/agent`

Esta carpeta contiene la logica central del agente de patentes: configuracion,
ensamblado del agente ADK, memoria, herramientas e instrucciones. Es el nucleo que
la API y los scripts consumen para resolver consultas.

El agente se mantiene agnostico del canal. Hoy puede ser consumido por:
- la API HTTP de `src/api`
- la UI de pruebas
- clientes manuales y scripts locales
- el adaptador Webex, de forma indirecta, a traves de `POST /chat`

## Como se compone

- `core/`: orquestacion del agente, esquemas y ayudas de ejecucion.
- `memory/`: almacenamiento y acceso al indice SQLite, sesiones y transcripcion.
- `prompts/`: instrucciones del agente (sistema, politicas, herramientas).
- `sources/`: conectores externos previos al indexado (hoy SharePoint).
- `tools/`: funciones expuestas al agente para buscar patentes.
- Archivos raiz: configuracion, registro y exportaciones del paquete.

## Rol de cada archivo

### Archivos raiz
- `__init__.py`: exporta ayudas principales del agente.
- `config.py`: carga `.env`, valida variables, define la fuente activa y resuelve rutas por defecto.
- `config.py`: tambien define parametros de polling incremental para SharePoint.
- `logging_config.py`: configura registro centralizado, rotacion y log de indexado.
- `debug_trace.py`: almacena trazas tecnicas de herramientas para `/chat_debug`.

### `core/`
- `__init__.py`: descripcion del paquete y lineamientos.
- `agent.py`: construye el agente ADK, carga instrucciones y ejecuta mensajes.
- `schemas.py`: dataclasses usadas por herramientas y respuestas.
- `planner.py`: planificador minimo (provisorio) para pasos del agente.
- `executor.py`: ejecutor simple (provisorio) para planes.

### `memory/`
- `__init__.py`: descripcion del paquete de memoria.
- `short_term.py`: sesiones ADK con persistencia local.
- `long_term.py`: marcador de posicion para memoria persistente futura.
- `vector_store.py`: indice SQLite, normalizacion, extraccion de campos y busqueda.
- `transcript.py`: persistencia de conversaciones en JSONL, incluyendo canal de origen cuando existe.

### `prompts/`
- `system.md`: instrucciones principales del agente.
- `policies.md`: reglas y limites de comportamiento.
- `tools.md`: especificacion de herramientas disponibles.

### `sources/`
- `__init__.py`: descripcion del paquete.
- `sharepoint_client.py`: autenticacion Graph con certificado PFX, listado de archivos, sync incremental a cache local y telemetria de requests/bytes.

### `tools/`
- `__init__.py`: lineamientos para herramientas del agente.
- `base.py`: tipos comunes para resultados de herramientas.
- `patente_search.py`: herramienta `buscar_patente` y registro de herramientas.

## Consejos y buenas practicas

- Mantene `.env` fuera de git y usa `.env.example` sin secretos.
- Si cambias el indice, reejecuta `scripts/index_patentes.py`.
- Usa `DOCS_BASE_URL` para que los enlaces apunten a la API correcta.
- Si `PATENTES_SOURCE_MODE=sharepoint`, el backend sirve PDFs desde `data/sharepoint_cache`.
- Al agregar campos en el indice, actualiza `schemas.py` y `tools.md`.
- Evita agregar logica de negocio en `memory/` o `tools/` sin documentarla.
- Si agregas nuevas herramientas, actualiza las instrucciones y los casos de eval.
- El modo `fuzzy` solo se usa si el usuario lo pide de forma explicita.
- Consultas estadisticas globales no se responden sin uso de herramientas.
