"""The ETL: raw parquet -> staging -> marts in DuckDB, then the data tests. Fails loudly if a test finds rows."""

from __future__ import annotations

from pathlib import Path

import duckdb

from ccf.config import RAW, WAREHOUSE

SQL = Path(__file__).parent / "sql"


def tests(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    text = (SQL / "03_tests.sql").read_text()
    out = {}
    for block in text.split("-- name: ")[1:]:
        name, query = block.split("\n", 1)
        out[name.strip()] = len(con.execute(query.strip().rstrip(";")).fetchall())
    return out


def run(raw: Path = RAW, warehouse: Path = WAREHOUSE) -> dict[str, int]:
    warehouse.unlink(missing_ok=True)
    con = duckdb.connect(str(warehouse))
    for name in ("01_staging.sql", "02_marts.sql"):
        con.execute((SQL / name).read_text().replace("{raw}", str(raw)))
    failed = {k: v for k, v in tests(con).items() if v}
    con.close()
    if failed:
        raise RuntimeError(f"data tests failed: {failed}")
    return {"tests_passed": len(tests(duckdb.connect(str(warehouse), read_only=True)))}


def connect(warehouse: Path = WAREHOUSE) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(warehouse), read_only=True)
