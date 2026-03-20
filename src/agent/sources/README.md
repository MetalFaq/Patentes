<!-- NOTA: Documentacion del paquete de fuentes externas del agente. -->
# Carpeta `src/agent/sources`

Esta carpeta encapsula conectores de origen que preparan datos antes del indexado.
No reemplaza al indice ni a las herramientas del agente; solo acerca archivos o
metadatos desde sistemas externos hacia el mirror local que luego usa `memory/`.

## Contenido

- `__init__.py`: descripcion breve del paquete.
- `sharepoint_client.py`: autenticacion con Graph, resolucion de site/biblioteca,
  listado de PDFs, descarga incremental, manifest local y telemetria operativa.

## Flujo esperado

1. Resolver configuracion SharePoint desde `.env`.
2. Validar acceso mediante requests GET (site, drives, carpeta).
3. Descargar PDFs nuevos o modificados al cache local.
4. Reusar `scripts/index_patentes.py` sobre ese cache.

## Que telemetria expone

El cliente devuelve, por corrida de sync:

- requests JSON a Graph
- requests de descarga de contenido
- bytes descargados
- cantidad de tokens solicitados
- respuestas `429`
- reuse del cache (`cache_hit_ratio`)

Esto permite monitorear costo tecnico y frecuencia sin mezclarlo con el costo del
modelo LLM.

## Scheduling actual

El proyecto no usa triggers nativos de SharePoint. La operacion actual es:

- polling incremental
- cada `N` minutos dentro de una ventana laboral
- indexado posterior solo si hubo cambios remotos

El scheduler que ejecuta esa estrategia vive en `scripts/sharepoint_scheduler.py`.

## Alcance

- No hay logica de negocio del agente en esta carpeta.
- No hay consultas al modelo.
- No hay busqueda semantica.
- Solo sincronizacion y preparacion de fuente de datos.

## Buenas practicas

- Mantener el certificado PFX fuera de git.
- No registrar tokens ni passphrases.
- Documentar cualquier cambio de protocolo o endpoint Graph.
- Si se cambia el formato del manifest local, actualizar `doc/SHAREPOINT_INTEGRACION.md`.
- Si cambias la telemetria o la frecuencia operativa, actualizar `doc/SHAREPOINT_OPERACION_Y_COSTOS.md`.
