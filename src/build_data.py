import tempfile
from pathlib import Path

import duckdb

from src.config import DB, RAW, ROOT, TABLES, TABLE_TYPES


def build():
    missing = [name for name in TABLES.values() if not (RAW / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Run python -m src.fetch_data first. Missing CSVs: {missing}")
    DB.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a fully built database. A failed build leaves the previous database usable.
    with tempfile.TemporaryDirectory(dir=DB.parent) as staging:
        candidate = Path(staging) / DB.name
        with duckdb.connect(str(candidate)) as con:
            for table, name in TABLES.items():
                con.execute(
                    f"CREATE TABLE raw_{table} AS SELECT * FROM read_csv(?, all_varchar=true)",
                    [str(RAW / name)],
                )
                for column, sql_type in TABLE_TYPES.get(table, {}).items():
                    con.execute(f'ALTER TABLE raw_{table} ALTER COLUMN "{column}" TYPE {sql_type}')
            for script in sorted((ROOT / "sql").glob("*.sql")):
                con.execute(script.read_text())
        candidate.replace(DB)
    print(f"Built {DB.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
