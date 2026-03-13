"""Utilidad de inspeccion de la base SQLite del indice.

Instrucciones:
- Mostrar estadisticas basicas del indice.
- Consultar coincidencias exactas, por prefijo, por contiene o fuzzy.
- Exportar resultados a CSV para revision manual.
- El modo fuzzy es solo para inspeccion; no lo usa el agente por defecto.
"""

import argparse
import csv
import sqlite3
from pathlib import Path

from agent.config import load_settings
from agent.logging_config import setup_logging
from agent.memory.vector_store import normalize_plate


def _connect(db_path: Path) -> sqlite3.Connection:
    """Abre una conexion SQLite simple para lectura."""
    return sqlite3.connect(db_path)


def _show_stats(conn: sqlite3.Connection) -> None:
    """Imprime conteos por tabla del indice."""
    tables = ["documents", "pages", "plate_hits"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")


def _compact_text(text: str, limit: int = 200) -> str:
    """Devuelve un fragmento corto de texto para inspeccion rapida."""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _show_plate(conn: sqlite3.Connection, plate: str, mode: str) -> None:
    """Muestra coincidencias segun el modo (exacto, prefijo, contiene o fuzzy)."""
    plate_norm = normalize_plate(plate)
    mode_norm = (mode or "exacto").strip().lower()
    if mode_norm not in {"exacto", "prefijo", "contiene", "fuzzy"}:
        print("Modo invalido. Usa exacto, prefijo, contiene o fuzzy.")
        return

    exact_rows = []
    sub_rows = []
    if mode_norm == "exacto":
        exact_rows = conn.execute(
            """
            SELECT plate_raw, doc_path, page_num, snippet,
                   poliza, certificado, asegurado,
                   vigencia_desde, vigencia_hasta, vehiculo, cobertura
            FROM plate_hits
            WHERE plate_norm = ?
            """,
            (plate_norm,),
        ).fetchall()

        sub_rows = conn.execute(
            """
            SELECT doc_path, page_num, text
            FROM pages
            WHERE text_norm LIKE ?
            """,
            (f"%{plate_norm}%",),
        ).fetchall()
    elif mode_norm in {"prefijo", "contiene"}:
        like_pattern = f"{plate_norm}%" if mode_norm == "prefijo" else f"%{plate_norm}%"
        rows = conn.execute(
            """
            SELECT plate_raw, plate_norm, doc_path, page_num, snippet,
                   poliza, certificado, asegurado,
                   vigencia_desde, vigencia_hasta, vehiculo, cobertura
            FROM plate_hits
            WHERE plate_norm LIKE ?
            ORDER BY plate_norm
            """,
            (like_pattern,),
        ).fetchall()

        if not rows:
            print("Sin resultados para la patente indicada.")
            return

        seen = set()
        unique_rows = []
        for row in rows:
            plate_norm_row = row[1]
            if plate_norm_row in seen:
                continue
            seen.add(plate_norm_row)
            unique_rows.append(row)

        print(
            f"Coincidencias por {mode_norm}: {len(rows)} (patentes unicas: {len(unique_rows)})"
        )
        for row in unique_rows:
            print(row)
        return
    else:
        sub_rows = conn.execute(
            """
            SELECT doc_path, page_num, text
            FROM pages
            WHERE text_norm LIKE ?
            """,
            (f"%{plate_norm}%",),
        ).fetchall()

    if not exact_rows and not sub_rows:
        print("Sin resultados para la patente indicada.")
        return

    if exact_rows:
        print(f"Coincidencias exactas: {len(exact_rows)}")
        for row in exact_rows:
            print(row)

    if sub_rows:
        print(f"Coincidencias por subcadena: {len(sub_rows)}")
        for doc_path, page_num, text in sub_rows:
            snippet = _compact_text(text)
            print((doc_path, page_num, snippet))


def _export_csv(conn: sqlite3.Connection, csv_path: Path, plate: str | None) -> None:
    """Exporta filas del indice a CSV, con filtro opcional por patente."""
    plate_norm = normalize_plate(plate) if plate else None
    query = """
        SELECT plate_raw, doc_path, page_num, snippet,
               poliza, certificado, asegurado,
               vigencia_desde, vigencia_hasta, vehiculo, cobertura
        FROM plate_hits
    """
    params = ()
    if plate_norm:
        query += " WHERE plate_norm = ?"
        params = (plate_norm,)

    rows = conn.execute(query, params).fetchall()
    headers = [
        "plate_raw",
        "doc_path",
        "page_num",
        "snippet",
        "poliza",
        "certificado",
        "asegurado",
        "vigencia_desde",
        "vigencia_hasta",
        "vehiculo",
        "cobertura",
    ]

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Exportado a {csv_path}")


def main() -> None:
    """Punto de entrada de la utilidad de inspeccion."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Inspeccion de la base de indices")
    parser.add_argument("--stats", action="store_true", help="Mostrar conteos")
    parser.add_argument(
        "--plate",
        type=str,
        help="Consultar una patente (usa --mode exacto, prefijo, contiene o fuzzy)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["exacto", "prefijo", "contiene", "fuzzy"],
        default="exacto",
        help="Modo de busqueda para --plate",
    )
    parser.add_argument("--export-csv", type=str, help="Exportar resultados a CSV")
    args = parser.parse_args()

    settings = load_settings()
    db_path = Path(settings.index_db)
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base: {db_path}")

    with _connect(db_path) as conn:
        if args.stats:
            _show_stats(conn)
        if args.plate:
            _show_plate(conn, args.plate, args.mode)
        if args.export_csv:
            _export_csv(conn, Path(args.export_csv), args.plate)


if __name__ == "__main__":
    main()
