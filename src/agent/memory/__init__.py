"""Paquete de memoria para el agente de patentes.

Instrucciones:
- La memoria de corto plazo usa sesiones ADK con persistencia local.
- La memoria de largo plazo es un componente provisorio para almacenamiento futuro.
- El indice SQLite vive en vector_store.py y es la base de busqueda.
- Evita agregar logica de negocio en este paquete sin documentarla.
"""
