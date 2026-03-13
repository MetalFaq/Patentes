<!-- NOTA: Documentacion de la carpeta de evaluacion para el agente de patentes. -->
# Evaluacion del agente

Este directorio contiene casos de prueba y un ejecutor simple para validar el comportamiento del agente.
La idea es detectar regresiones cuando cambian instrucciones, herramientas o logica.

## Archivos

- `conversations.json`: lista de casos con `input` y una expectativa textual.
- `eval_agent.py`: archivo que carga los casos, ejecuta el agente y muestra respuestas.

## Que informacion guardan

### `conversations.json`
- `_docstring`: nota interna para mantener el archivo corto.
- `cases[]`: cada caso tiene:
  - `input`: mensaje del usuario.
  - `expectation`: criterio de evaluacion manual o futura asercion.

### `eval_agent.py`
- Carga configuracion desde `.env`.
- Inicializa el agente con sus herramientas reales.
- Ejecuta cada caso y muestra la respuesta.

## Como se generan los casos

- Manual: agregar nuevos objetos en `cases[]` con entradas reales.
- Recomendado: capturar preguntas frecuentes del negocio y casos limite.
- Incluir ejemplos de modos `prefijo` y `contiene` cuando se quiera validar esas rutas.

## Para que sirven

- Verificar que el agente usa `buscar_patente` correctamente.
- Comparar resultados entre versiones de instrucciones o herramientas.
- Base para automatizar evaluaciones en integracion continua.

## Preguntas de prueba (UI)

1. Buscá el dominio ILD070 y pasame el link del PDF.
2. Necesito los datos del seguro del dominio IJB108.
3. Mostrame la poliza y certificado del dominio ADE018.
4. Que informacion tenes para el dominio AC348SV?
5. Buscá el dominio AD472QA y devolveme el documento.
6. Quiero el detalle del seguro del dominio AD978NA.
7. Consultá el dominio NDN786.
8. Buscá el dominio AE721WY y decime si existe en el indice.
9. Necesito el link y pagina del dominio AC687HI.
10. Mostrame los datos completos del dominio AD414GG.
11. Listame dominios que empiecen con AD.
12. Mostrame dominios que empiecen con AC.
13. Buscá dominios que contengan 87.
14. Dominios que contengan 70.
15. Listame dominios que empiecen con AE.

## Como ejecutar

```powershell
$env:PYTHONPATH=".\src"
python eval/eval_agent.py
```

Si queres automatizar aserciones, podes convertir `expectation` en verificaciones concretas.
El agente responde en modo exacto por defecto; solo usa `fuzzy` si el usuario lo pide.
