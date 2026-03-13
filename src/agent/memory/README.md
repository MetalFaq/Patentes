<!-- NOTA: Documentacion de src/agent/memory. Mantener en espanol y sin secretos. -->
# Carpeta `src/agent/memory`

Esta carpeta agrupa la memoria y los mecanismos de persistencia del agente:
sesiones de corto plazo, indice SQLite para patentes y registro de conversaciones.
Su objetivo es almacenar y recuperar informacion sin depender del modelo.

## Como se compone

- `vector_store.py`: indice SQLite, extraccion y busqueda de patentes.
- `short_term.py`: sesiones ADK con persistencia local.
- Usa metodos async para evitar warnings deprecados.
- `long_term.py`: base minima para memoria persistente futura.
- `transcript.py`: guardado de conversaciones en JSONL.
- `__init__.py`: descripcion del paquete y lineamientos.

## Rol de cada archivo

### `vector_store.py`
- Construye y mantiene el indice SQLite.
- Extrae patentes y campos del PDF.
- Prioriza etiquetas DOMINIO/PATENTE/MATRICULA/PLACA para reducir falsos positivos.
- Valida formatos de dominio antes de insertar en el indice.
- Devuelve coincidencias con enlace a documento y pagina.
- Indica si la coincidencia es exacta, prefijo, contiene o subcadena (modo fuzzy).
- Expone `dominio_label` y paginas asociadas a etiquetas (`label_pages`).
- Registra errores de extraccion en `data/logs/patentes_agent.index_errors.log`.
- Registra tiempos por PDF y tiempo total de cada corrida de indexado.

### `short_term.py`
- Administra sesiones de usuario en memoria con respaldo en disco.
- Permite retomar contexto dentro de un mismo usuario/sesion.

### `long_term.py`
- Marcador de posicion para perfiles persistentes o historicos.
- Evita almacenar secretos o datos sensibles sin reglas claras.

### `transcript.py`
- Guarda cada intercambio en formato JSONL.
- Facilita auditoria y depuracion basica.
- Puede registrar el canal de origen (`api`, `webex`, etc.) cuando el cliente lo informa.

### `__init__.py`
- Resume el proposito del paquete de memoria.
- Mantiene reglas de uso para el resto del proyecto.

## Consejos y buenas practicas

- Si cambias el esquema del indice, reindexa con `scripts/index_patentes.py`.
- Mantene `vector_store.py` libre de llamadas al modelo.
- Si agregas campos nuevos, actualiza `tools.md` y `schemas.py`.
- Evita guardar datos sensibles en la transcripcion sin consentimiento.
- El modo `fuzzy` solo se usa bajo pedido explicito.
