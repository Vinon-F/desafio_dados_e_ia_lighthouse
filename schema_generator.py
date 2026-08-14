import os
import csv
import re
from datetime import datetime
import unicodedata

# ==========================================
# CONFIGURATIONS
# ==========================================

CSV_DIR = 'csv' # Directory for reading .csv files 
OUTPUT_SQL = 'schema.sql' # The file will be generated in the project root

# Type hierarchy: from weakest (0) to strongest (5)
# If a weaker type is found, the entire column downgrades to the weaker type.
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
    """
    Removes accents, spaces, and special characters to create 
    valid PostgreSQL identifiers.
    """
    # Removes accents
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    # Replaces anything non-alphanumeric with an underscore
    name = re.sub(r'[^\w]', '_', name)
    # Removes duplicate underscores
    name = re.sub(r'_+', '_', name)
    # Strips underscores from the beginning/end
    name = name.strip('_')
    # Avoids starting with a number (PostgreSQL doesn't allow it)
    if name and name[0].isdigit():
        name = f'col_{name}'
    return name.lower()

def infer_value_type(value):
    """
    Analyzes an individual string and returns the presumed PostgreSQL type.
    Returns None if the string is empty.
    """
    val = value.strip()
    if not val:
        return None

    # 1. Boolean
    if val.lower() in ('true', 'false', 't', 'f', 'yes', 'no', 'sim', 'nao'):
        return 'BOOLEAN'

    # 2. Integer vs Identification Codes (Tax IDs, Phones, etc)
    # lstrip('-') ensures negative numbers work properly
    if val.lstrip('-').isdigit():
        clean_val = val.lstrip('-')
        
        # HEURISTIC 1: Leading Zeros
        # If a number has a leading zero (e.g., "01234"), it's an ID/code, NOT a math integer.
        if len(clean_val) > 1 and clean_val.startswith('0'):
            return 'TEXT'
            
        # HEURISTIC 2: Absurd Length
        # Standard database INTEGERs don't exceed 10 digits (up to ~2.1 billion).
        # If it's longer than 12 digits, it's likely a Tax ID, Phone, or Hash.
        # We force it to TEXT to avoid BIGINT and keep it as a raw string identifier.
        if len(clean_val) > 12:
            return 'TEXT'

        # HEURISTIC 3: Standard Integers (Fallback)
        # If it passed the tests above, it's a normal quantity. Map to INTEGER or BIGINT.
        int_val = int(val)
        PG_INT_MAX = 2147483647
        if int_val <= PG_INT_MAX:
            return 'INTEGER'
        else:
            return 'BIGINT'

    # 3. Numeric (Float/Decimal)
    try:
        float(val)
        # If it has a decimal point or comma, it's numeric
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

    # 6. Fallback to Text
    return 'TEXT'

def process_csv(file_path):
    """
    Reads a CSV file and returns a list of tuples: (sanitized_column_name, pg_type)
    """
    table_name = os.path.splitext(os.path.basename(file_path))[0]
    table_name = sanitize_name(table_name)
    
    columns_types = {}

    # Opens CSV with utf-8 encoding and error replacement (common in ERPs)
    with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        
        try:
            header = next(reader)
        except StopIteration:
            print(f"WARNING: File {file_path} is empty. Skipped.")
            return None, None

        # Initializes columns with None (type undefined yet)
        for col in header:
            sanitized_col = sanitize_name(col)
            # Avoids duplicate column names after sanitization (e.g., "Name" and "Name ")
            base_name = sanitized_col
            counter = 1
            while sanitized_col in columns_types:
                sanitized_col = f"{base_name}_{counter}"
                counter += 1
                
            columns_types[sanitized_col] = None

        # Maps CSV index to the sanitized name
        index_map = {i: sanitize_name(header[i]) for i in range(len(header))}

        # Reads data rows
        for row in reader:
            for idx, cell_value in enumerate(row):
                if idx not in index_map:
                    continue # Ignores extra columns that might appear mid-file
                
                col_name = index_map[idx]
                current_type = columns_types[col_name]
                candidate_type = infer_value_type(cell_value)

                # If the cell is empty, keeps the current type
                if candidate_type is None:
                    continue
                
                # If it's the first definition
                if current_type is None:
                    columns_types[col_name] = candidate_type
                # If the candidate is weaker than the current, downgrades the type
                elif TYPE_RANK[candidate_type] < TYPE_RANK[current_type]:
                    columns_types[col_name] = candidate_type

    # If the entire column is null/empty, defaults to TEXT for safety
    final_types = {col: (dtype if dtype is not None else 'TEXT') for col, dtype in columns_types.items()}
    
    return table_name, final_types

def generate_sql(table_name, final_types):
    """Builds the CREATE TABLE DDL string for PostgreSQL"""
    sql_columns = []
    for column, dtype in final_types.items():
        sql_columns.append(f"    {column} {dtype}")
    
    # Adds a comma at the end of each line, except the last one
    definition = ",\n".join(sql_columns)
    
    sql = f"-- {table_name} \n"
    sql += f"CREATE TABLE IF NOT EXISTS {table_name} (\n{definition}\n);\n\n"
    return sql

def main():
    # Checks if the directory actually exists before proceeding
    if not os.path.isdir(CSV_DIR):
        print(f"ERROR: The directory '{CSV_DIR}' was not found.")
        print("Please ensure the 'csv' folder exists at the same level as this script.")
        return

    csv_files = [f for f in os.listdir(CSV_DIR) if f.lower().endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found inside '{CSV_DIR}/'")
        return

    sql_outputs = []
    
    # SQL file header
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

    # Writes the final file
    with open(OUTPUT_SQL, mode='w', encoding='utf-8') as f:
        f.writelines(sql_outputs)
        
    print(f"\nSuccess! File '{OUTPUT_SQL}' created at the project root.")

if __name__ == "__main__":
    main()