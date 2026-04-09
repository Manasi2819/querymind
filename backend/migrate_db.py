"""
migrate_db.py
───────────────────────────────────────────────────────────────────────────────
Standalone Database Migration CLI Script

Migrates ALL data from a source database to a target database.
Handles SQLite -> MySQL/PostgreSQL and any other SQLAlchemy-compatible pair.

Usage:
  python migrate_db.py <SOURCE_DB_URL> <TARGET_DB_URL>

Examples:
  python migrate_db.py "sqlite:///./querymind_metadata.db" "mysql+pymysql://root:admin@localhost:3306/queryminddb"
  python migrate_db.py "sqlite:///./querymind_metadata.db" "postgresql+psycopg2://user:pass@host:5432/queryminddb"

Run from: backend/ directory
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, MetaData, inspect

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("migrate_db")

# ── Table order (parent before child) ────────────────────────────────────────
TABLE_ORDER = [
    "admin_users",
    "admin_settings",
    "uploaded_files",
    "chat_sessions",
    "chat_messages",
]

BATCH_SIZE = 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_mysql(url: str) -> bool:
    return url.lower().startswith("mysql")


def _is_sqlite(url: str) -> bool:
    return url.lower().startswith("sqlite")


def _build_engine(url: str):
    if _is_sqlite(url):
        return create_engine(url, connect_args={"check_same_thread": False})
    elif _is_mysql(url):
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600)
    else:
        return create_engine(url, pool_pre_ping=True)


def _coerce_row(row: dict, source_url: str, target_url: str) -> dict:
    """Parse SQLite string-encoded JSON into dicts when target is MySQL/PG."""
    if not _is_sqlite(source_url):
        return row
    coerced = {}
    for key, value in row.items():
        if isinstance(value, str) and not _is_sqlite(target_url):
            stripped = value.strip()
            if stripped.startswith(("{", "[")):
                try:
                    coerced[key] = json.loads(stripped)
                    continue
                except (json.JSONDecodeError, ValueError):
                    pass
        coerced[key] = value
    return coerced


def _tables_in_source(inspector) -> list:
    existing = set(inspector.get_table_names())
    return [t for t in TABLE_ORDER if t in existing]


def _count_sql(url: str, table: str) -> str:
    if _is_mysql(url):
        return f"SELECT COUNT(*) FROM `{table}`"
    return f'SELECT COUNT(*) FROM "{table}"'


def _validate(src_conn, tgt_conn, tables: list, source_url: str, target_url: str) -> bool:
    logger.info("")
    logger.info("=" * 60)
    logger.info("POST-MIGRATION VALIDATION")
    logger.info("=" * 60)
    all_pass = True
    for table in tables:
        try:
            src_n = src_conn.execute(text(_count_sql(source_url, table))).scalar()
            tgt_n = tgt_conn.execute(text(_count_sql(target_url, table))).scalar()
            ok = src_n == tgt_n
            label = "PASS" if ok else "FAIL"
            logger.info(f"  {label}  {table:<25}  source={src_n}  target={tgt_n}")
            if not ok:
                all_pass = False
        except Exception as exc:
            logger.warning(f"  SKIP  {table:<25}  {exc}")
    logger.info("=" * 60)
    return all_pass


# ── Migration ─────────────────────────────────────────────────────────────────

def migrate(source_url: str, target_url: str) -> None:
    logger.info("")
    logger.info("=" * 60)
    logger.info("QueryMind Database Migration Tool")
    logger.info("=" * 60)
    logger.info(f"  Source : {source_url}")
    logger.info(f"  Target : {target_url}")
    logger.info("=" * 60)

    # ── Step 1: Auto-create target DB ────────────────────────────────────
    logger.info("\n[Step 1] Initializing target database...")
    try:
        from core.db_init import initialize_database
        initialize_database(target_url)
    except Exception as exc:
        logger.warning(f"[Step 1] Auto-create skipped: {exc}")

    # ── Step 2: Create schema on target ──────────────────────────────────
    # We reflect the source schema into a FRESH MetaData object and then
    # reproduce it on the target. This avoids ORM MetaData conflicts.
    # Note: SQLite allows unbounded VARCHAR, MySQL requires explicit lengths.
    # We normalize all unbounded String columns to VARCHAR(512) before
    # creating tables on the target.
    logger.info("\n[Step 2] Creating schema on target database...")
    try:
        from sqlalchemy import String as SAString
        from sqlalchemy.types import NullType

        target_engine = _build_engine(target_url)
        tmp_meta = MetaData()
        tmp_src = _build_engine(source_url)
        tmp_meta.reflect(bind=tmp_src)
        tmp_src.dispose()

        # Normalize VARCHAR columns for MySQL compatibility
        if _is_mysql(target_url):
            for table in tmp_meta.tables.values():
                for col in table.columns:
                    if isinstance(col.type, (SAString, NullType)):
                        if not getattr(col.type, "length", None):
                            col.type = SAString(512)

        tmp_meta.create_all(bind=target_engine)
        logger.info("[Step 2] Schema created on target database.")
    except Exception as exc:
        import traceback
        logger.error(f"[Step 2] Schema creation failed: {exc}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # ── Step 3: Reflect source for row-copy ──────────────────────────────
    logger.info("\n[Step 3] Reflecting source tables...")
    source_engine = _build_engine(source_url)
    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)
    inspector = inspect(source_engine)

    tables = _tables_in_source(inspector)
    logger.info(f"[Step 3] Tables to migrate: {tables}")

    # ── Step 4: Copy rows ────────────────────────────────────────────────
    logger.info("\n[Step 4] Migrating data...")
    total_rows = 0

    with source_engine.connect() as src_conn, target_engine.begin() as tgt_conn:

        if _is_mysql(target_url):
            logger.info("  [MySQL] Disabling foreign key checks...")
            tgt_conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

        for table_name in tables:
            logger.info(f"\n  Migrating: [{table_name}]")

            if table_name not in source_meta.tables:
                logger.warning(f"  Not found in source. Skipping.")
                continue

            src_table = source_meta.tables[table_name]
            row_count = src_conn.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar()
            logger.info(f"  Source rows: {row_count}")

            if row_count == 0:
                logger.info("  (Empty — skipping)")
                continue

            rows_done = 0
            offset = 0

            while True:
                batch = src_conn.execute(
                    src_table.select().limit(BATCH_SIZE).offset(offset)
                ).fetchall()
                if not batch:
                    break

                batch_dicts = [
                    _coerce_row(dict(row._mapping), source_url, target_url)
                    for row in batch
                ]

                # Use the target table's insert() for fully dialect-safe inserts.
                # This avoids the PyMySQL "dict cannot be used as parameter" error
                # that occurs when using raw text() with a list of dicts.
                tgt_table = target_engine.connect()
                # Get the reflected table from the target
                tgt_meta_ref = MetaData()
                tgt_meta_ref.reflect(bind=target_engine)
                if table_name in tgt_meta_ref.tables:
                    tgt_tbl = tgt_meta_ref.tables[table_name]
                    tgt_conn.execute(tgt_tbl.insert(), batch_dicts)
                else:
                    # Fallback: text insert
                    columns = list(batch_dicts[0].keys())
                    if _is_mysql(target_url):
                        col_str = ", ".join(f"`{c}`" for c in columns)
                        val_str = ", ".join(f":{c}" for c in columns)
                        sql = text(f"INSERT INTO `{table_name}` ({col_str}) VALUES ({val_str})")
                    else:
                        col_str = ", ".join(f'"{c}"' for c in columns)
                        val_str = ", ".join(f":{c}" for c in columns)
                        sql = text(f'INSERT INTO "{table_name}" ({col_str}) VALUES ({val_str})')
                    tgt_conn.execute(sql, batch_dicts)

                rows_done += len(batch)
                offset += BATCH_SIZE

                if row_count > BATCH_SIZE:
                    logger.info(f"  ... {rows_done}/{row_count} rows done")

            logger.info(f"  {rows_done} rows migrated -> [{table_name}]")
            total_rows += rows_done

        if _is_mysql(target_url):
            logger.info("\n  [MySQL] Re-enabling foreign key checks...")
            tgt_conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    logger.info(f"\n[Step 4] Done. {len(tables)} tables, {total_rows} total rows.")

    # ── Step 5: Validate ─────────────────────────────────────────────────
    logger.info("\n[Step 5] Validating row counts...")
    with source_engine.connect() as sc, target_engine.connect() as tc:
        all_pass = _validate(sc, tc, tables, source_url, target_url)

    if all_pass:
        logger.info("\nMigration SUCCESSFUL - all row counts match!")
        logger.info(f"\n  Next: update your .env file:")
        logger.info(f"    DATABASE_URL={target_url}")
        logger.info(f"  Then restart: uvicorn main:app --reload --port 8000\n")
    else:
        logger.error("\nMigration completed with row count mismatches. Review above.")

    source_engine.dispose()
    target_engine.dispose()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("\nUsage:")
        print('  python migrate_db.py "<SOURCE_DB_URL>" "<TARGET_DB_URL>"\n')
        print("Examples:")
        print('  python migrate_db.py "sqlite:///./querymind_metadata.db" "mysql+pymysql://root:admin@localhost:3306/queryminddb"')
        print('  python migrate_db.py "sqlite:///./querymind_metadata.db" "postgresql+psycopg2://user:pass@host:5432/queryminddb"')
        sys.exit(1)

    migrate(sys.argv[1], sys.argv[2])
