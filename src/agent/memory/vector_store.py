"""Indice en SQLite para PDFs de patentes.

Instrucciones:
- Este modulo es responsable del esquema del indice y la E/S.
- No llames al modelo desde aqui.
- Mantene la normalizacion consistente con las herramientas de busqueda.
- Si cambias el esquema, forza reindexado y actualiza herramientas y esquemas.
- Prioriza etiquetas DOMINIO/PATENTE/MATRICULA/PLACA para evitar falsos positivos.
- Solo registra dominios validos (AAA999 o AA999AA).
- Registra errores de extraccion en el log dedicado de indexado.
- El modo fuzzy es opcional y solo se usa bajo pedido explicito.
- Expone paginas de etiquetas mediante get_label_pages().
- Registra tiempo total de indexado y tiempos por PDF (logs + salida JSON).
"""

from dataclasses import dataclass
from pathlib import Path
import logging
import os
import re
import sqlite3
import urllib.parse
import time
from typing import Dict, List, Optional

try:
    from pypdf import PdfReader
except ImportError as exc:
    raise ImportError("Se requiere pypdf. Instala con: pip install pypdf") from exc


logger = logging.getLogger(__name__)
index_error_logger = logging.getLogger("agent.index")

PLATE_PATTERNS = [
    re.compile(r"\b([A-Z]{2,3})[\s-]?(\d{3,4})([A-Z]{0,2})\b"),
    re.compile(r"\b([A-Z]{1,2})[\s-]?(\d{3})[\s-]?([A-Z]{2})\b"),
]
LABEL_PATTERN = re.compile(
    r"(?:DOMINIO|PATENTE|MATR[ÍI]CULA(?:\s*/\s*PLACA)?|PLACA)\s*[:\-]?\s*([A-Z0-9\-\s]{3,20})"
)
VALID_MATCH_MODES = {"exacto", "prefijo", "contiene"}
VALID_PLATE_PATTERNS = [
    re.compile(r"^[A-Z]{3}\d{3}$"),
    re.compile(r"^[A-Z]{2}\d{3}[A-Z]{2}$"),
]
LABEL_PLATE_PATTERNS = [
    re.compile(r"[A-Z]{3}\d{3}"),
    re.compile(r"[A-Z]{2}\d{3}[A-Z]{2}"),
]


def normalize_plate(value: str) -> str:
    """Normaliza una patente a mayusculas alfanumericas."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def normalize_text(value: str) -> str:
    """Normaliza el texto para busqueda por subcadena."""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def is_valid_plate(value: str) -> bool:
    """Valida formatos de dominio/patente aceptados."""
    plate_norm = normalize_plate(value)
    if not plate_norm:
        return False
    return any(pattern.fullmatch(plate_norm) for pattern in VALID_PLATE_PATTERNS)


def build_file_link(path: Path, page_number: int) -> str:
    """Construye un enlace HTTP al PDF con pagina.

    Usa DOCS_BASE_URL y una ruta relativa a la fuente.
    """
    base_url = os.getenv("DOCS_BASE_URL", "http://localhost:8000").rstrip("/")
    source_env = os.getenv("PATENTES_SOURCE_DIR")
    rel_path = path.name
    if source_env:
        try:
            rel_path = str(path.resolve().relative_to(Path(source_env).resolve()))
        except ValueError:
            rel_path = path.name
    rel_path = rel_path.replace("\\", "/")
    rel_path = urllib.parse.quote(rel_path)
    return f"{base_url}/docs/{rel_path}#page={page_number}"


def _extract_matches(text: str) -> List[Dict[str, int | str]]:
    """Extrae posibles patentes del texto.

    Prioriza coincidencias etiquetadas como DOMINIO/PATENTE para evitar falsos positivos.
    """
    matches: List[Dict[str, int | str]] = []
    labeled = list(LABEL_PATTERN.finditer(text.upper()))
    if labeled:
        for match in labeled:
            label_value = match.group(1)
            label_norm = normalize_plate(label_value)
            plate_raw = None
            for pattern in LABEL_PLATE_PATTERNS:
                candidate = pattern.search(label_norm)
                if candidate and is_valid_plate(candidate.group(0)):
                    plate_raw = candidate.group(0)
                    break
            if not plate_raw:
                continue
            matches.append(
                {
                    "plate": plate_raw,
                    "start": match.start(1),
                    "end": match.end(1),
                }
            )
        if matches:
            return matches

    text_upper = text.upper()
    for pattern in PLATE_PATTERNS:
        for match in pattern.finditer(text_upper):
            plate_raw = match.group(0)
            if not is_valid_plate(plate_raw):
                continue
            matches.append(
                {
                    "plate": plate_raw,
                    "start": match.start(0),
                    "end": match.end(0),
                }
            )
    return matches


def _make_snippet(text: str, start: int, end: int, window: int = 60) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right].replace("\n", " ").strip()
    return re.sub(r"\s+", " ", snippet)


def _extract_fields(text: str) -> Dict[str, Optional[str]]:
    """Extrae campos relevantes del texto cuando hay Dominio/Patente."""
    text_upper = text.upper()
    if not re.search(r"(DOMINIO|PATENTE|MATR[ÍI]CULA|PLACA)", text_upper):
        return {}

    fields: Dict[str, Optional[str]] = {
        "poliza": None,
        "certificado": None,
        "asegurado": None,
        "vigencia_desde": None,
        "vigencia_hasta": None,
        "vehiculo": None,
        "cobertura": None,
        "dominio": None,
        "dominio_label": None,
    }

    def _find(pattern: str, flags: int = re.IGNORECASE | re.MULTILINE) -> Optional[str]:
        match = re.search(pattern, text, flags=flags)
        if not match:
            return None
        value = match.group(1).strip()
        return value if value else None

    date_token = r"([0-3]?\d/[01]?\d/\d{2,4})"
    rango = re.search(
        rf"VIGENCIA[\s\S]{{0,160}}?{date_token}[\s\S]{{0,80}}?{date_token}",
        text,
        flags=re.IGNORECASE,
    )
    if rango:
        fields["vigencia_desde"] = rango.group(1).strip()
        fields["vigencia_hasta"] = rango.group(2).strip()
    else:
        fields["vigencia_desde"] = _find(
            rf"(?:VIGENCIA[\s\S]{{0,80}}?)?DESDE(?:\s+LAS\s+\d{{1,2}}\s*HS\.?)?\s*{date_token}"
        )
        fields["vigencia_hasta"] = _find(
            rf"(?:VIGENCIA[\s\S]{{0,80}}?)?HASTA(?:\s+LAS\s+\d{{1,2}}\s*HS\.?)?\s*{date_token}"
        )

    if not fields["vigencia_desde"] or not fields["vigencia_hasta"]:
        dates = re.findall(date_token, text)
        ordered_dates: list[str] = []
        for current_date in dates:
            if current_date not in ordered_dates:
                ordered_dates.append(current_date)
        if len(ordered_dates) >= 2:
            fields["vigencia_desde"] = fields["vigencia_desde"] or ordered_dates[0]
            fields["vigencia_hasta"] = fields["vigencia_hasta"] or ordered_dates[1]

    fields["poliza"] = _find(
        r"(?:POLIZA|P[ÓO]LIZA)\s*(?:N[°ºO]\.?)?\s*[:\-]?\s*([A-Z0-9\-]{5,})"
    )
    fields["certificado"] = _find(
        r"CERTIFICADO\s*(?:N[°ºO]\.?)?\s*[:\-]?\s*([A-Z0-9\-]{1,})"
    )
    fields["asegurado"] = _find(
        r"ASEGURADO(?:\s*\([^\)]*\))?\s*(?:N[°ºO]\.?)?\s*[:\-]?\s*([^\n\r|]+)"
    )
    fields["vehiculo"] = _find(r"VEHICULO\s*[:\-]?\s*(.+)")
    fields["cobertura"] = _find(r"COBERTURA\s*[:\-]?\s*(.+)")

    label_match = LABEL_PATTERN.search(text_upper)
    if label_match:
        label_value = label_match.group(1)
        label_norm = normalize_plate(label_value)
        for pattern in LABEL_PLATE_PATTERNS:
            candidate = pattern.search(label_norm)
            if candidate and is_valid_plate(candidate.group(0)):
                fields["dominio"] = candidate.group(0)
                label_text = label_match.group(0).split(":")[0].strip().upper()
                label_text = label_text.replace("MATRÍCULA / PLACA", "MATRICULA")
                label_text = label_text.replace("MATRÍCULA", "MATRICULA")
                label_text = label_text.replace("PLACA", "PLACA")
                fields["dominio_label"] = label_text
                break

    return fields


@dataclass(frozen=True)
class PlateHit:
    """Coincidencia de patente dentro del indice."""
    plate: str
    document_path: str
    page_number: int
    snippet: str
    document_link: str
    match_type: str = "exacto"
    poliza: Optional[str] = None
    certificado: Optional[str] = None
    asegurado: Optional[str] = None
    vigencia_desde: Optional[str] = None
    vigencia_hasta: Optional[str] = None
    vehiculo: Optional[str] = None
    cobertura: Optional[str] = None
    dominio_label: Optional[str] = None


class PlateIndex:
    """Gestor del indice para fuentes PDF y busqueda de patentes.

    Administra esquema SQLite, indexado y consultas.
    """

    def __init__(self, db_path: Path, source_dir: Path):
        self.db_path = Path(db_path)
        self.source_dir = Path(source_dir)

    def _connect(self) -> sqlite3.Connection:
        """Abre una conexion SQLite con pragmas de rendimiento."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        """Crea tablas e indices si no existen."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_path TEXT PRIMARY KEY,
                mtime REAL NOT NULL,
                page_count INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_path TEXT NOT NULL,
                page_num INTEGER NOT NULL,
                text TEXT NOT NULL,
                text_norm TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plate_hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_norm TEXT NOT NULL,
                plate_raw TEXT NOT NULL,
                doc_path TEXT NOT NULL,
                page_num INTEGER NOT NULL,
                snippet TEXT NOT NULL,
                poliza TEXT,
                certificado TEXT,
                asegurado TEXT,
                vigencia_desde TEXT,
                vigencia_hasta TEXT,
                vehiculo TEXT,
                cobertura TEXT,
                dominio_label TEXT
            )
            """
        )
        self._ensure_columns(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plate_hits_plate ON plate_hits(plate_norm)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pages_doc ON pages(doc_path)"
        )
        existing_indexes = {
            row[1] for row in conn.execute("PRAGMA index_list(plate_hits)").fetchall()
        }
        if "idx_plate_hits_unique" not in existing_indexes:
            conn.execute(
                """
                DELETE FROM plate_hits
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM plate_hits
                    GROUP BY plate_norm, doc_path, page_num
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_plate_hits_unique
                ON plate_hits(plate_norm, doc_path, page_num)
                """
            )

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        """Agrega columnas nuevas a plate_hits cuando faltan."""
        columns = {
            "poliza": "TEXT",
            "certificado": "TEXT",
            "asegurado": "TEXT",
            "vigencia_desde": "TEXT",
            "vigencia_hasta": "TEXT",
            "vehiculo": "TEXT",
            "cobertura": "TEXT",
            "dominio_label": "TEXT",
        }
        existing = {
            row[1] for row in conn.execute("PRAGMA table_info(plate_hits)").fetchall()
        }
        for column, col_type in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE plate_hits ADD COLUMN {column} {col_type}")

    def index_source(
        self,
        force: bool = False,
        limit: Optional[int] = None,
        max_pages_per_pdf: Optional[int] = None,
        site: Optional[str] = None,
        log_every: int = 10,
    ) -> dict:
        """Indexa todos los PDFs del directorio fuente en SQLite.

        Usa limites opcionales para pruebas rapidas, loguea progreso y
        saltea paginas que fallen en la extraccion de texto.
        Tambien devuelve trazabilidad de tiempos (total y por PDF).
        """
        base_dir = self.source_dir
        if site:
            candidate = (self.source_dir / site).resolve()
            try:
                candidate.relative_to(self.source_dir.resolve())
            except ValueError as exc:
                raise FileNotFoundError(
                    f"Directorio fuente no encontrado: {candidate}"
                ) from exc
            base_dir = candidate

        if not base_dir.exists():
            raise FileNotFoundError(f"Directorio fuente no encontrado: {base_dir}")

        stats = {
            "pdfs_indexed": 0,
            "pages_indexed": 0,
            "plate_hits": 0,
            "skipped": 0,
            "index_time_seconds": 0.0,
            "pdf_timings": [],
        }

        pdf_paths = sorted(base_dir.rglob("*.pdf"))
        processed = 0
        total_start = time.perf_counter()

        with self._connect() as conn:
            self._ensure_schema(conn)
            cursor = conn.cursor()

            for pdf_path in pdf_paths:
                if limit is not None and processed >= limit:
                    break

                pdf_start = time.perf_counter()
                mtime = pdf_path.stat().st_mtime
                row = cursor.execute(
                    "SELECT mtime FROM documents WHERE doc_path = ?",
                    (str(pdf_path),),
                ).fetchone()

                if row and not force and abs(row[0] - mtime) < 0.0001:
                    stats["skipped"] += 1
                    processed += 1
                    pdf_elapsed = round(time.perf_counter() - pdf_start, 3)
                    stats["pdf_timings"].append(
                        {
                            "pdf_path": str(pdf_path),
                            "status": "skipped",
                            "elapsed_seconds": pdf_elapsed,
                            "pages_indexed": 0,
                            "plate_hits_added": 0,
                        }
                    )
                    logger.info(
                        "PDF omitido %s | tiempo=%.3fs",
                        pdf_path.name,
                        pdf_elapsed,
                    )
                    continue

                hits_before_pdf = stats["plate_hits"]

                cursor.execute("DELETE FROM pages WHERE doc_path = ?", (str(pdf_path),))
                cursor.execute("DELETE FROM plate_hits WHERE doc_path = ?", (str(pdf_path),))

                reader = PdfReader(str(pdf_path))
                page_count = 0

                for index, page in enumerate(reader.pages, start=1):
                    if max_pages_per_pdf and index > max_pages_per_pdf:
                        break

                    try:
                        text = page.extract_text() or ""
                    except KeyboardInterrupt:
                        raise
                    except Exception as exc:
                        index_error_logger.warning(
                            "No se pudo extraer texto de %s pagina %s",
                            pdf_path,
                            index,
                            exc_info=exc,
                        )
                        continue
                    if not text.strip():
                        continue

                    text_norm = normalize_text(text)
                    cursor.execute(
                        "INSERT INTO pages (doc_path, page_num, text, text_norm) VALUES (?, ?, ?, ?)",
                        (str(pdf_path), index, text, text_norm),
                    )
                    page_count += 1

                    fields = _extract_fields(text)
                    seen_plates = set()
                    for match in _extract_matches(text):
                        plate_raw = str(match["plate"])
                        plate_norm = normalize_plate(plate_raw)
                        if not plate_norm:
                            continue
                        key = (plate_norm, str(pdf_path), index)
                        if key in seen_plates:
                            continue
                        seen_plates.add(key)
                        snippet = _make_snippet(text, int(match["start"]), int(match["end"]))
                        before_changes = conn.total_changes
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO plate_hits (
                                plate_norm,
                                plate_raw,
                                doc_path,
                                page_num,
                                snippet,
                                poliza,
                                certificado,
                                asegurado,
                                vigencia_desde,
                                vigencia_hasta,
                                vehiculo,
                                cobertura,
                                dominio_label
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                plate_norm,
                                plate_raw,
                                str(pdf_path),
                                index,
                                snippet,
                                fields.get("poliza"),
                                fields.get("certificado"),
                                fields.get("asegurado"),
                                fields.get("vigencia_desde"),
                                fields.get("vigencia_hasta"),
                                fields.get("vehiculo"),
                                fields.get("cobertura"),
                                fields.get("dominio_label"),
                            ),
                        )
                        if conn.total_changes > before_changes:
                            stats["plate_hits"] += 1

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO documents (doc_path, mtime, page_count)
                    VALUES (?, ?, ?)
                    """,
                    (str(pdf_path), mtime, page_count),
                )

                stats["pdfs_indexed"] += 1
                stats["pages_indexed"] += page_count
                processed += 1

                pdf_elapsed = round(time.perf_counter() - pdf_start, 3)
                hits_added = stats["plate_hits"] - hits_before_pdf
                stats["pdf_timings"].append(
                    {
                        "pdf_path": str(pdf_path),
                        "status": "indexed",
                        "elapsed_seconds": pdf_elapsed,
                        "pages_indexed": page_count,
                        "plate_hits_added": hits_added,
                    }
                )
                logger.info(
                    "PDF indexado %s | paginas=%s | hits=%s | tiempo=%.3fs",
                    pdf_path.name,
                    page_count,
                    hits_added,
                    pdf_elapsed,
                )

                if log_every and processed % log_every == 0:
                    logger.info("Procesados %s PDFs", processed)

        stats["index_time_seconds"] = round(time.perf_counter() - total_start, 3)
        logger.info(
            "Indexado finalizado | pdfs_indexados=%s | paginas_indexadas=%s | plate_hits=%s | omitidos=%s | tiempo_total=%.3fs",
            stats["pdfs_indexed"],
            stats["pages_indexed"],
            stats["plate_hits"],
            stats["skipped"],
            stats["index_time_seconds"],
        )
        return stats

    def search(self, plate: str, limit: int = 5, mode: str = "exacto") -> List[PlateHit]:
        """Busca en el indice una patente y devuelve coincidencias.

        Modos:
        - exacto: coincidencia exacta en plate_hits.
        - prefijo: plate_norm comienza con el valor dado.
        - contiene: plate_norm contiene el valor dado.
        - fuzzy: busca coincidencias en texto completo de paginas.

        El campo match_type indica el tipo de coincidencia.
        """
        mode_norm = (mode or "exacto").strip().lower()
        if mode_norm not in VALID_MATCH_MODES and mode_norm != "fuzzy":
            mode_norm = "exacto"

        plate_norm = normalize_plate(plate)
        if not plate_norm:
            return []

        hits: List[PlateHit] = []
        if not self.db_path.exists():
            return hits

        with self._connect() as conn:
            self._ensure_schema(conn)
            cursor = conn.cursor()
            if mode_norm == "exacto":
                rows = cursor.execute(
                    """
                    SELECT plate_raw, doc_path, page_num, snippet,
                           poliza, certificado, asegurado,
                           vigencia_desde, vigencia_hasta, vehiculo, cobertura, dominio_label
                    FROM plate_hits
                    WHERE plate_norm = ?
                    LIMIT ?
                    """,
                    (plate_norm, limit),
                ).fetchall()

                for (
                    plate_raw,
                    doc_path,
                    page_num,
                    snippet,
                    poliza,
                    certificado,
                    asegurado,
                    vigencia_desde,
                    vigencia_hasta,
                    vehiculo,
                    cobertura,
                    dominio_label,
                ) in rows:
                    hits.append(
                        PlateHit(
                            plate=plate_raw,
                            document_path=doc_path,
                            page_number=page_num,
                            snippet=snippet,
                            document_link=build_file_link(Path(doc_path), page_num),
                            match_type="exacto",
                            poliza=poliza,
                            certificado=certificado,
                            asegurado=asegurado,
                            vigencia_desde=vigencia_desde,
                            vigencia_hasta=vigencia_hasta,
                            vehiculo=vehiculo,
                            cobertura=cobertura,
                            dominio_label=dominio_label,
                        )
                    )
                return hits

            if mode_norm in {"prefijo", "contiene"}:
                like_pattern = f"{plate_norm}%" if mode_norm == "prefijo" else f"%{plate_norm}%"
                rows = cursor.execute(
                    """
                    SELECT plate_raw, plate_norm, doc_path, page_num, snippet,
                           poliza, certificado, asegurado,
                           vigencia_desde, vigencia_hasta, vehiculo, cobertura, dominio_label
                    FROM plate_hits
                    WHERE plate_norm LIKE ?
                    ORDER BY plate_norm
                    LIMIT ?
                    """,
                    (like_pattern, limit),
                ).fetchall()

                seen = set()
                for (
                    plate_raw,
                    plate_norm_row,
                    doc_path,
                    page_num,
                    snippet,
                    poliza,
                    certificado,
                    asegurado,
                    vigencia_desde,
                    vigencia_hasta,
                    vehiculo,
                    cobertura,
                    dominio_label,
                ) in rows:
                    if plate_norm_row in seen:
                        continue
                    seen.add(plate_norm_row)
                    hits.append(
                        PlateHit(
                            plate=plate_raw,
                            document_path=doc_path,
                            page_number=page_num,
                            snippet=snippet,
                            document_link=build_file_link(Path(doc_path), page_num),
                            match_type=mode_norm,
                            poliza=poliza,
                            certificado=certificado,
                            asegurado=asegurado,
                            vigencia_desde=vigencia_desde,
                            vigencia_hasta=vigencia_hasta,
                            vehiculo=vehiculo,
                            cobertura=cobertura,
                            dominio_label=dominio_label,
                        )
                    )
                return hits

            if mode_norm == "fuzzy":
                like_pattern = f"%{plate_norm}%"
                rows = cursor.execute(
                    """
                    SELECT doc_path, page_num, text
                    FROM pages
                    WHERE text_norm LIKE ?
                    LIMIT ?
                    """,
                    (like_pattern, limit),
                ).fetchall()

                for doc_path, page_num, text in rows:
                    snippet = _make_snippet(text, 0, min(len(text), 1), window=120)
                    hits.append(
                        PlateHit(
                            plate=plate_norm,
                            document_path=doc_path,
                            page_number=page_num,
                            snippet=snippet,
                            document_link=build_file_link(Path(doc_path), page_num),
                            match_type="subcadena",
                        )
                    )

        return hits

    def get_label_pages(self, plate_norm: str) -> Dict[str, List[Dict[str, object]]]:
        """Devuelve paginas por etiqueta (DOMINIO/PATENTE/MATRICULA/PLACA)."""
        if not plate_norm or not self.db_path.exists():
            return {}

        label_pages: Dict[str, List[Dict[str, object]]] = {}
        with self._connect() as conn:
            self._ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT dominio_label, doc_path, page_num
                FROM plate_hits
                WHERE plate_norm = ?
                  AND dominio_label IS NOT NULL
                ORDER BY page_num
                """,
                (plate_norm,),
            ).fetchall()

        seen = set()
        for dominio_label, doc_path, page_num in rows:
            label = (dominio_label or "").strip().upper()
            if not label:
                continue
            key = (label, doc_path, page_num)
            if key in seen:
                continue
            seen.add(key)
            label_pages.setdefault(label, []).append(
                {
                    "page_number": page_num,
                    "document_link": build_file_link(Path(doc_path), page_num),
                }
            )
        return label_pages
