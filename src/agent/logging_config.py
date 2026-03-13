"""Configuracion centralizada de registro para el agente de patentes.

Instrucciones:
- Escribir registros en data/logs/ con rotacion por tamanio.
- Separar registros generales y de error.
- No reconfigurar manejadores si ya existen (evita duplicados).
- Usar esta configuracion en scripts y en el inicio de la API.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from agent.config import project_root


def setup_logging() -> None:
    """Configura registro con rotacion y archivos separados.

    Crea:
    - patentes_agent.log (INFO)
    - patentes_agent.error.log (ERROR)
    - patentes_agent.index_errors.log (WARNING, errores de indexado)
    """
    root_logger = logging.getLogger()

    log_dir = project_root() / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "patentes_agent.log"
    err_file = log_dir / "patentes_agent.error.log"
    index_err_file = log_dir / "patentes_agent.index_errors.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    if not root_logger.handlers:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        err_handler = RotatingFileHandler(
            err_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(err_handler)
        root_logger.addHandler(console_handler)

    index_logger = logging.getLogger("agent.index")
    if not any(
        isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", "") == str(index_err_file)
        for handler in index_logger.handlers
    ):
        index_handler = RotatingFileHandler(
            index_err_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        index_handler.setLevel(logging.WARNING)
        index_handler.setFormatter(formatter)
        index_logger.addHandler(index_handler)
        index_logger.propagate = True
