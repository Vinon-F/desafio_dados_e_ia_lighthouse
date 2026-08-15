import os
import csv
import re
from datetime import datetime
import unicodedata

CSV_DIR = 'csv'
OUTPUT_SQL = 'schema.sql'

TYPE_RANK = {
    'TEXT': 0,
    'DATE': 1,
    'TIMESTAMP': 2,
    'NUMERIC': 3,
    'BIGINT': 4,
    'INTEGER': 5,
    'BOOLEAN': 6
}

def sanitize_name(name):

    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = re.sub(r'[^\w]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    if name and name[0].isdigit():
        name = f'col_{name}'
    return name.lower()

def infer_value_type(value):
    val = value.strip()
    if not val:
        return None

    # 1. Boolean
    if val.lower() in ('true', 'false', 't', 'f', 'yes', 'no', 'sim', 'nao'):
        return 'BOOLEAN'

    # 2. Integer
    if val.lstrip('-').isdigit():
        clean_val = val.lstrip('-')
        
        # HEURISTIC 1: Números começando com 0.. Ex: 01312
        if len(clean_val) > 1 and clean_val.startswith('0'):
            return 'TEXT'
            
        # HEURISTIC 2: Números com mais de 12 dígitos = Text
        if len(clean_val) > 12:
            return 'TEXT'

        # HEURISTIC 3: Fallback interno para Inteiros.
        int_val = int(val)
        PG_INT_MAX = 2147483647
        if int_val <= PG_INT_MAX:
            return 'INTEGER'
        else:
            return 'BIGINT'

    # 3. Numeric (Float/Decimal)
    try:
        float(val)
        if '.' in val or ',' in val:
            return 'NUMERIC'
    except ValueError:
        pass

    # 4. Timestamp (YYYY-MM-DD HH:MM:SS or with milliseconds)
    ts_formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S'
    ]
    for fmt in ts_formats:
        try:
            datetime.strptime(val, fmt)
            return 'TIMESTAMP'
        except ValueError:
            continue

    # 5. Date (YYYY-MM-DD)
    try:
        datetime.strptime(val, '%Y-%m-%d')
        return 'DATE'
    except ValueError:
        pass

    # 6. Fallback para Text
    return 'TEXT'

def process_csv(file_path):
    table_name = os.path.splitext(os.path.basename(file_path))[0]
    table_name = sanitize_name(table_name)
    
    columns_types = {}

    with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        
        try:
            header = next(reader)
        except StopIteration:
            print(f"WARNING: File {file_path} is empty. Skipped.")
            return None, None

        for col in header:
            sanitized_col = sanitize_name(col)
            base_name = sanitized_col
            counter = 1
            while sanitized_col in columns_types:
                sanitized_col = f"{base_name}_{counter}"
                counter += 1
                
            columns_types[sanitized_col] = None

        index_map = {i: sanitize_name(header[i]) for i in range(len(header))}

        for row in reader:
            for idx, cell_value in enumerate(row):
                if idx not in index_map:
                    continue 
                
                col_name = index_map[idx]
                current_type = columns_types[col_name]
                candidate_type = infer_value_type(cell_value)

                if candidate_type is None:
                    continue
                
                if current_type is None:
                    columns_types[col_name] = candidate_type
                elif TYPE_RANK[candidate_type] < TYPE_RANK[current_type]:
                    columns_types[col_name] = candidate_type

    final_types = {col: (dtype if dtype is not None else 'TEXT') for col, dtype in columns_types.items()}
    
    return table_name, final_types

def generate_sql(table_name, final_types):
    """Builds the CREATE TABLE DDL string for PostgreSQL"""
    sql_columns = []
    for column, dtype in final_types.items():
        sql_columns.append(f"    {column} {dtype}")
    
    definition = ",\n".join(sql_columns)
    
    sql = f"-- {table_name} \n"
    sql += f"CREATE TABLE IF NOT EXISTS {table_name} (\n{definition}\n);\n\n"
    return sql

def main():
    if not os.path.isdir(CSV_DIR):
        print(f"ERROR: The directory '{CSV_DIR}' was not found.")
        print("Please ensure the 'csv' folder exists at the same level as this script.")
        return

    csv_files = [f for f in os.listdir(CSV_DIR) if f.lower().endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found inside '{CSV_DIR}/'")
        return

    sql_outputs = []
    
    sql_outputs.append("-- DB_Schema \n")
    sql_outputs.append("-- Target: PostgreSQL\n\n")

    for file_name in sorted(csv_files):
        full_path = os.path.join(CSV_DIR, file_name)
        print(f"Processing: {file_name}...")
        
        table_name, final_types = process_csv(full_path)
        
        if table_name and final_types:
            generated_sql = generate_sql(table_name, final_types)
            sql_outputs.append(generated_sql)
            print(f"  -> Table '{table_name}' mapped successfully ({len(final_types)} columns).")

    with open(OUTPUT_SQL, mode='w', encoding='utf-8') as f:
        f.writelines(sql_outputs)
        
    print(f"\nSuccess! File '{OUTPUT_SQL}' created at the project root.")

if __name__ == "__main__":
    main()