<!-- NOTA: Documentacion de src/agent/core. Mantener en espanol y sin secretos. -->
# Carpeta `src/agent/core`

Esta carpeta concentra la logica de orquestacion del agente: armado de instrucciones,
construccion del agente ADK, ejecucion de mensajes y esquemas de datos internos.
Es el punto de integracion entre instrucciones, herramientas y memoria.

## Como se compone

- `agent.py`: crea el agente y ejecuta mensajes de usuario.
- `schemas.py`: define estructuras de datos para respuestas internas.
- `planner.py`: planificador minimo (provisorio) para pasos del agente.
- `executor.py`: ejecutor simple (provisorio) para planes.
- `__init__.py`: descripcion del paquete y lineamientos generales.

## Rol de cada archivo

### `agent.py`
- Carga instrucciones desde `src/agent/prompts`.
- Ensambla el agente ADK con herramientas y configuracion.
- Ejecuta mensajes y consolida texto de respuesta.
- Controla errores y deja registro en archivos de registros.
- Registra trazas tecnicas de herramientas para `/chat_debug`.
- Evita responder estadisticas globales si no hubo herramientas.

### `schemas.py`
- Centraliza clases de datos usadas en herramientas.
- Asegura consistencia entre indice, herramientas y respuestas de API.

### `planner.py`
- Devuelve un plan basico de pasos del agente.
- Se mantiene deterministico para no introducir ruido.

### `executor.py`
- Ejecuta planes simples y devuelve pasos.
- Sirve como reemplazo provisorio para estrategias mas complejas.

### `__init__.py`
- Define el alcance del paquete `core`.
- Refuerza que aqui vive la logica de orquestacion.

## Consejos y buenas practicas

- Si cambias instrucciones o herramientas, actualiza los casos en `eval/`.
- No incrustes secretos en `agent.py`; usa `.env`.
- Mantene `schemas.py` estable para evitar rupturas aguas abajo.
- Si agregas un planificador real, ajusta `planner.py` y `executor.py`.
