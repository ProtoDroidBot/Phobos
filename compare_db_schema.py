import sqlite3

REFERENCE_DB = r"C:\Users\deimos\Desktop\starmap_stillness.db"
GENERATED_DB = r"test_schema.db"

def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [(row[1], row[2]) for row in cursor.fetchall()]  # (name, type)
        schema[table] = columns
    conn.close()
    return schema

def print_schema(schema, title):
    print(f"\nSchema for {title}:")
    for table, columns in schema.items():
        print(f"Table: {table}")
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")
        print()

def compare_schemas(ref_schema, gen_schema):
    print("\nComparison:")
    for table in ref_schema:
        if table not in gen_schema:
            print(f"Missing table in generated DB: {table}")
            continue
        ref_cols = dict(ref_schema[table])
        gen_cols = dict(gen_schema[table])
        for col, col_type in ref_cols.items():
            if col not in gen_cols:
                print(f"Missing column in table '{table}': {col}")
            elif gen_cols[col].upper() != col_type.upper():
                print(f"Type mismatch in table '{table}', column '{col}': {col_type} (ref) vs {gen_cols[col]} (gen)")
    print("\nAll required tables and columns exist in generated DB if no warnings above.")

def main():
    ref_schema = get_schema(REFERENCE_DB)
    gen_schema = get_schema(GENERATED_DB)
    print_schema(ref_schema, "Reference DB")
    print_schema(gen_schema, "Generated DB")
    compare_schemas(ref_schema, gen_schema)

if __name__ == "__main__":
    main()
