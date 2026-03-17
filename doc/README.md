<!-- NOTA: Documentacion operativa del proyecto. Mantener en espanol y sin secretos. -->
# Carpeta `doc`

Esta carpeta concentra notas operativas que no pertenecen al README funcional del
proyecto, pero que si son necesarias para llevar `Patentes` desde un entorno local
hacia uno productivo.

## Contenido

- `ARQUITECTURA_GENERAL.md`: vista completa del sistema, desde el indexado hasta Webex.
- `ENDPOINTS_PUBLICOS_ESTABLES.md`: resumen practico para pedir infraestructura estable y dejar de depender de tuneles.
- `LOGS_Y_OBSERVABILIDAD.md`: detalle de cada log, persistencia tecnica y archivo de diagnostico.
- `REQUERIMIENTO_TECNICO_INFRAESTRUCTURA.md`: pedido formal para Infra/Cloud/Seguridad con fundamentos y criterio de aceptacion.
- `TUNEL_PUBLICO.md`: teoria y practica de tuneles HTTPS temporales para pruebas locales.
- `MIGRACION_PRODUCCION.md`: cambios de arquitectura, red, secretos y persistencia para salir de `localhost`.
- `WEBEX_WEBHOOK.md`: pasos concretos para crear y operar el webhook de Webex.
- `PRUEBA_END_TO_END.md`: circuito completo de prueba local con backend, adaptador, tunel y mensaje real.

## Alcance

Estos documentos cubren:
- arquitectura general del proyecto
- publicacion del backend de Patentes
- publicacion del adaptador Webex
- reemplazo de `localhost:8000` y `localhost:8010`
- DNS, HTTPS y tuneles de prueba
- funcionamiento de webhook y deduplicacion
- circuito de prueba total
- observabilidad y diagnostico por archivo
- endpoints HTTPS estables y requisitos de infraestructura
- pedido formal de infraestructura con fundamentos tecnicos
- gestion de secretos
- persistencia de `WEBEX_DEDUPE_STORE`, sesiones y transcript

Varios documentos incluyen diagramas en formato Mermaid para explicar el flujo
de datos y la operacion completa del sistema.

Mientras no exista reachability publica confiable para el webhook, la UI local
del backend (`http://localhost:8000/ui`) sigue siendo la superficie de prueba
vigente para validar el agente.
