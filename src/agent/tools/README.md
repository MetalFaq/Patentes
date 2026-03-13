<!-- NOTA: Documentacion de src/agent/tools. Mantener en espanol y sin secretos. -->
# Carpeta `src/agent/tools`

Esta carpeta define las herramientas que el agente puede invocar. Cada
herramienta es una funcion con entrada/salida serializable en JSON y con un
contrato claro para el modelo.

## Como se compone

- `patente_search.py`: herramienta principal `buscar_patente`.
- `base.py`: tipos comunes para resultados de herramientas.
- `__init__.py`: lineamientos del paquete y convenciones.

## Rol de cada archivo

### `patente_search.py`
- Resuelve busquedas en el indice SQLite.
- Devuelve coincidencias con enlace a documento y pagina.
- Indica el tipo de coincidencia con `match_type` (exacto, prefijo, contiene o subcadena).
- Usa modo exacto por defecto.
- Acepta `modo` para forzar prefijo, contiene o fuzzy cuando el usuario lo pide.
- Evita usar `fuzzy` salvo pedido explicito del usuario.
- Si existen etiquetas distintas (DOMINIO vs MATRICULA/PLACA), retorna paginas agrupadas.
- Es la unica herramienta expuesta al agente en esta version.

### `base.py`
- Define estructuras comunes para estandarizar resultados.
- Facilita validaciones y contratos consistentes.

### `__init__.py`
- Explica reglas de diseño de herramientas.
- Indica donde se registran las herramientas disponibles.

## Consejos y buenas practicas

- Mantene las herramientas deterministas y sin efectos colaterales.
- No llames al modelo desde tools; usa solo memoria/indice.
- Si agregas una herramienta nueva, actualiza `prompts/tools.md`.
- Agrega validacion de entrada cerca del limite de la herramienta.
