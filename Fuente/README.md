# Fuente Local de Documentos (PDFs de Pólizas y Coberturas)

Esta carpeta sirve como directorio de entrada local cuando el agente opera con `PATENTES_SOURCE_MODE=local`.

## Estructura esperada:

Coloque en este directorio (o en subcarpetas organizadas por empresa o unidad de negocio) los archivos PDF correspondientes a las constancias de cobertura o pólizas de automotores:

```text
Fuente/
├── Empresa_A/
│   └── Constancia_Cobertura_Poliza_001.pdf
├── Empresa_B/
│   └── Constancia_Cobertura_Poliza_002.pdf
└── Flota_Motos/
    └── Cobertura_Motos.pdf
```

## Formato de los documentos:

- **Formato:** Archivos `.pdf` legibles (texto digital o escaneos con OCR).
- **Contenido indexado:** Dominio/Patente del vehículo, número de póliza, compañía aseguradora, vigencia y entidad asegurada.
- **Indexación:** Ejecute `python scripts/index_documents.py` para procesar los PDFs e indexarlos en la base de datos local SQLite (`data/index/patentes.sqlite`).

> [!NOTE]
> Todos los archivos PDF dentro de esta carpeta están ignorados por el `.gitignore` para prevenir la exposición de información corporativa o personal.
