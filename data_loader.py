import os
import time
import csv
import re
import logging
import unicodedata
from typing import Any, List
import psycopg2  # pip install psycopg2-binary
from psycopg2 import sql
from psycopg2.extras import execute_values
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()

CSV_DIR = 'csv'
BATCH_SIZE = 10000  # Number of rows to insert per batch (optimizes performance)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

def sanitize_name(name: str) -> str:
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = re.sub(r'[^\w]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    if name and name[0].isdigit():
        name = f'col_{name}'
    return name.lower()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def get_table_columns(cur: Any, table_name: str) -> List[str]:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return [row[0] for row in cur.fetchall()]

def parse_value(value: str) -> Any:
    if value == '':
        return None
    return value

# ==========================================
# MAIN LOGIC
# ==========================================

def load_csv_file(file_path: str, conn: Any) -> bool:

    start_time = time.time()

    table_name = os.path.splitext(os.path.basename(file_path))[0]
    table_name = sanitize_name(table_name)

    try:
        with conn.cursor() as cur:
            columns_in_db = get_table_columns(cur, table_name)

            if not columns_in_db:
                logger.warning(f"Table '{table_name}' does not exist in the database. Skipping.")
                return False

            with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)

                try:
                    header = next(reader)
                except StopIteration:
                    logger.warning(f"File '{file_path}' is empty. Skipping.")
                    return False

                index_map = {}
                for idx, col in enumerate(header):
                    sanitized_col = sanitize_name(col)
                    if sanitized_col in columns_in_db:
                        index_map[idx] = sanitized_col

                unmatched = [col for col in header if sanitize_name(col) not in columns_in_db]
                if unmatched:
                    logger.warning(f"'{table_name}': headers not matched to any column: {unmatched}")

                if not index_map:
                    logger.warning(f"No matching columns found for table '{table_name}'. Skipping.")
                    return False

                columns = [index_map[idx] for idx in sorted(index_map.keys())]

                truncate_sql = sql.SQL("TRUNCATE TABLE {} CASCADE;").format(
                    sql.Identifier(table_name)
                )
                insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                    sql.Identifier(table_name),
                    sql.SQL(', ').join(sql.Identifier(c) for c in columns)
                )

                logger.info(f"Truncating '{table_name}' (CASCADE — dependent rows in other tables will also be removed).")
                cur.execute(truncate_sql)

                batch = []
                total_inserted = 0

                for row in reader:
                    row_values = []
                    for idx in sorted(index_map.keys()):
                        val = row[idx] if idx < len(row) else ''
                        row_values.append(parse_value(val))

                    batch.append(tuple(row_values))

                    if len(batch) >= BATCH_SIZE:
                        execute_values(cur, insert_sql, batch)
                        total_inserted += len(batch)
                        batch = []

                if batch:
                    execute_values(cur, insert_sql, batch)
                    total_inserted += len(batch)

        conn.commit()
        elapsed_time = time.time() - start_time
        logger.info(f"SUCCESS: Loaded {total_inserted} raw rows into '{table_name}' in {elapsed_time:.2f}s.")
        return True

    except psycopg2.errors.InvalidTextRepresentation as e:

        conn.rollback()
        logger.error(f"'{table_name}': incompatible data for column type. File not loaded. Details: {e}")
        return False

    except psycopg2.OperationalError as e:
        conn.rollback()
        logger.error(f"'{table_name}': database connection error. File not loaded. Details: {e}")
        return False

    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"'{table_name}': database error. File not loaded. Details: {e}")
        return False

def main() -> None:
    if not os.path.isdir(CSV_DIR):
        logger.error(f"The directory '{CSV_DIR}' was not found.")
        return

    csv_files = [f for f in os.listdir(CSV_DIR) if f.lower().endswith('.csv')]

    if not csv_files:
        logger.warning(f"No CSV files found inside '{CSV_DIR}/'")
        return

    logger.info("Starting database connection...")
    conn = get_db_connection()

    overall_start_time = time.time()
    succeeded, failed = [], []

    try:
        for file_name in sorted(csv_files):
            logger.info(f"Processing: {file_name}...")
            ok = load_csv_file(os.path.join(CSV_DIR, file_name), conn)
            (succeeded if ok else failed).append(file_name)

        total_elapsed = time.time() - overall_start_time
        logger.info(
            f"Data loading finished in {total_elapsed:.2f}s. "
            f"{len(succeeded)} succeeded, {len(failed)} failed/skipped."
        )
        if failed:
            logger.warning(f"Files not loaded: {failed}")

    finally:
        conn.close()
        logger.info("Database connection closed.")

if __name__ == "__main__":
    main()
