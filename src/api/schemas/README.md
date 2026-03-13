<!-- NOTA: Documentacion de src/api/schemas. Mantener en espanol y sin secretos. -->
# Carpeta `src/api/schemas`

Esta carpeta contiene los modelos de datos de la API (Pydantic). Su objetivo
es validar entradas y salidas para mantener un contrato estable con clientes.

## Como se compone

- `request.py`: modelos de solicitud.
- `response.py`: modelos de respuesta.
- `__init__.py`: reglas del paquete de esquemas.

## Rol de cada archivo

### `request.py`
- Define `ChatRequest` con los campos esperados del cliente.
- Incluye `channel` como campo opcional para registrar el origen del mensaje.

### `response.py`
- Define `ChatResponse` y `ChatDebugResponse` con el texto y datos de depuracion.
- `ChatDebugResponse.debug` contiene solo trazas tecnicas de herramientas.
- `text` puede incluir markdown con enlaces a documentos.

### `__init__.py`
- Lineamientos para mantener estabilidad de modelos.

## Consejos y buenas practicas

- Si cambias un campo, versiona la API o comunica el cambio.
- Mantene los campos descriptivos y con validacion clara.
- Evita campos opcionales innecesarios, salvo para trazabilidad o compatibilidad.
