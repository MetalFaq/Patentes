<!-- NOTA: Documentacion de src/api. Mantener en espanol y sin secretos. -->
# Carpeta `src/api`

Esta carpeta expone la API HTTP del agente. Su objetivo es recibir mensajes,
delegar la logica al paquete `src/agent` y devolver respuestas consistentes.
Mantiene las rutas delgadas y deja la inteligencia del sistema en el nucleo.

La API es el backend unico del agente y hoy es consumida por:
- la UI web de pruebas (`/ui`)
- clientes manuales via HTTP
- la CLI local (indirectamente)
- el adaptador Webex de `src/webex_adapter`

## Como se compone

- `main.py`: crea la app FastAPI, registra interceptores y rutas.
- `dependencies.py`: dependencias compartidas (agente, configuracion, sesiones).
- `routes/`: rutas HTTP (chat, debug, UI y documentos).
- `schemas/`: modelos de entrada y salida para validacion.
- `__init__.py`: reglas del paquete.

## Rol de cada archivo y subcarpeta

### `main.py`
- Inicializa FastAPI y monta las rutas.
- Registra el interceptor de transcripcion.
- Ejecuta la configuracion de registro al inicio.
- Conserva el backend desacoplado del canal Webex.

### `dependencies.py`
- Carga configuracion y memoriza objetos pesados.
- Expone creadores para agente y servicio de sesiones.

### `routes/`
- `chat.py`: rutas POST `/chat` y `/chat_debug`.
- `docs.py`: ruta GET `/docs/{rel_path}` para servir PDFs.
- `ui.py`: ruta GET `/ui` con interfaz web de pruebas.
- `__init__.py`: lineamientos para mantener rutas simples.
  - `chat_debug` devuelve trazas tecnicas de herramientas (no razonamiento interno).

### `schemas/`
- `request.py`: modelos Pydantic de entrada.
- `response.py`: modelos Pydantic de salida.
- `__init__.py`: descripcion del paquete de esquemas.

### `__init__.py`
- Reglas generales de la API y sus responsabilidades.

## Consejos y buenas practicas

- No agregues logica de negocio en las rutas.
- Si cambias los esquemas, avisa a los clientes.
- Usa `DOCS_BASE_URL` para enlaces correctos en entornos remotos.
- Mantene el interceptor simple para no afectar el rendimiento.
- Usa el campo opcional `channel` para trazabilidad del origen si el cliente lo conoce.
