<!-- NOTA: Guia de uso de herramientas. -->

# Herramienta disponible

1. buscar_patente
   - Proposito: buscar una patente en el indice local de PDFs.
   - Parametros:
     - placa (string): patente a buscar.
     - max_resultados (int, opcional): limite de coincidencias.
     - modo (string, opcional): exacto, prefijo, contiene o fuzzy.
   - Respuesta:
     - found (bool)
     - plate (string normalizada)
     - modo (string) usado en la busqueda
     - results[] con:
       - document_path
       - page_number
       - document_link
       - snippet
       - match_type (exacto, prefijo, contiene o subcadena)
       - poliza
       - certificado
       - asegurado
       - vigencia_desde
       - vigencia_hasta
       - vehiculo
       - cobertura
       - dominio_label (DOMINIO, PATENTE, MATRICULA o PLACA)
       - label_pages (paginas agrupadas por etiqueta)
   - Uso:
     - Si el usuario envia varias patentes, llama la herramienta una vez por patente.
     - Si el usuario pide \"empiecen con\" o \"prefijo\", usa modo \"prefijo\".
     - Si el usuario pide \"contenga\", usa modo \"contiene\".
     - Si el usuario pide coincidencias aproximadas o textuales, usa modo \"fuzzy\".
     - Si no hay resultados, solicita confirmacion o un formato alternativo.
     - En la respuesta al usuario, mostrar solo poliza, vigencia, asegurado y link, salvo pedido explicito.
     - En vigencia, siempre mostrar dos campos separados: vigencia_desde y vigencia_hasta.
     - El enlace al documento debe devolverse como hipervinculo Markdown: [Ver página N](URL).
