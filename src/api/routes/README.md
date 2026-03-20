<!-- NOTA: Documentacion de src/api/routes. Mantener en espanol y sin secretos. -->
# Carpeta `src/api/routes`

Esta carpeta define las rutas HTTP de la API. Cada ruta es delgada,
valida entradas y delega la logica al paquete `src/agent`.

## Como se compone

- `chat.py`: rutas POST `/chat` y `/chat_debug`.
- `docs.py`: ruta GET `/docs/{rel_path}` para servir PDFs.
- `ui.py`: ruta GET `/ui` con interfaz web de pruebas.
- `__init__.py`: reglas del paquete de rutas.

## Rol de cada archivo

### `chat.py`
- Recibe un mensaje del usuario.
- Llama al agente y devuelve la respuesta.
- Usa `ChatRequest`, `ChatResponse` y `ChatDebugResponse`.
- `chat_debug` devuelve trazas tecnicas de herramientas (no razonamiento interno).
- `/chat` es el contrato estable consumido por API manual, UI y adaptador Webex.
- El texto devuelto puede incluir markdown con links a PDFs.

### `docs.py`
- Resuelve rutas seguras dentro de la fuente activa del proyecto.
- Devuelve el PDF solicitado con `FileResponse`.
- En modo SharePoint sirve desde `data/sharepoint_cache`.

### `ui.py`
- Interfaz web simple para conversar con el agente.
- Muestra trazas tecnicas de herramientas.
- Consume `/chat_debug` para obtener la respuesta con trazas.
- Se usa como superficie de test para desarrolladores.

### `__init__.py`
- Lineamientos para mantener rutas simples y declarativas.

## Consejos y buenas practicas

- No agregues logica de negocio en rutas.
- Usa esquemas para validar entradas/salidas.
- Si agregas rutas nuevas, documentalas en README.
