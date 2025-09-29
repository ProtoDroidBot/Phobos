import sqlite3

REFERENCE_DB = r"C:\Users\deimos\Desktop\starmap_stillness.db"
GENERATED_DB = r"test_schema2.db"

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

def get_data_counts(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    counts = {}
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    
    conn.close()
    return counts

def get_sample_data(db_path, table_name, limit=5):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return columns, rows
    except sqlite3.Error as e:
        conn.close()
        return None, str(e)

def compare_data_integrity(ref_db, gen_db):
    print("\n=== DATA INTEGRITY COMPARISON ===")
    
    ref_counts = get_data_counts(ref_db)
    gen_counts = get_data_counts(gen_db)
    
    print("\nRecord Counts:")
    for table in ref_counts:
        ref_count = ref_counts.get(table, 0)
        gen_count = gen_counts.get(table, 0)
        status = "✅" if gen_count >= ref_count else "❌"
        print(f"  {table}: Reference={ref_count:,}, Generated={gen_count:,} {status}")
        
        if gen_count < ref_count:
            print(f"    ⚠️  Generated database has {ref_count - gen_count:,} fewer records")
    
    # Check for extra tables in generated DB
    extra_tables = set(gen_counts.keys()) - set(ref_counts.keys())
    if extra_tables:
        print(f"\nExtra tables in generated DB: {', '.join(extra_tables)}")
    
    return ref_counts, gen_counts

def compare_sample_data(ref_db, gen_db, table_mapping):
    print("\n=== SAMPLE DATA COMPARISON ===")
    
    for ref_table, gen_table in table_mapping.items():
        print(f"\nComparing {ref_table} -> {gen_table}:")
        
        ref_cols, ref_data = get_sample_data(ref_db, ref_table)
        gen_cols, gen_data = get_sample_data(gen_db, gen_table)
        
        if ref_cols is None or gen_cols is None:
            print(f"  ❌ Error reading data: {ref_data if ref_cols is None else gen_data}")
            continue
            
        # Check if reference columns exist in generated table
        missing_cols = []
        for col in ref_cols:
            if col not in gen_cols:
                missing_cols.append(col)
        
        if missing_cols:
            print(f"  ❌ Missing columns in generated table: {missing_cols}")
        else:
            print(f"  ✅ All reference columns present")
        
        # Show sample data structure
        print(f"  Reference columns: {ref_cols}")
        print(f"  Generated columns: {gen_cols}")
        
        if ref_data and gen_data:
            print(f"  Sample reference record: {ref_data[0]}")
            print(f"  Sample generated record: {gen_data[0]}")

def validate_data_relationships(db_path):
    print(f"\n=== RELATIONSHIP VALIDATION ===")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    checks = []
    
    # Check that all systems have valid constellation references
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM SolarSystems s 
            LEFT JOIN Constellations c ON s.constellationId = c.constellationId 
            WHERE s.constellationId IS NOT NULL AND c.constellationId IS NULL
        """)
        orphaned_systems = cursor.fetchone()[0]
        if orphaned_systems == 0:
            checks.append("✅ All systems have valid constellation references")
        else:
            checks.append(f"❌ {orphaned_systems} systems have invalid constellation references")
    except sqlite3.Error as e:
        checks.append(f"❌ Error checking system-constellation relationships: {e}")
    
    # Check that all constellations have valid region references  
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM Constellations c 
            LEFT JOIN Regions r ON c.regionId = r.regionId 
            WHERE c.regionId IS NOT NULL AND r.regionId IS NULL
        """)
        orphaned_constellations = cursor.fetchone()[0]
        if orphaned_constellations == 0:
            checks.append("✅ All constellations have valid region references")
        else:
            checks.append(f"❌ {orphaned_constellations} constellations have invalid region references")
    except sqlite3.Error as e:
        checks.append(f"❌ Error checking constellation-region relationships: {e}")
    
    # Check that all jumps reference valid systems
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM Jumps j 
            LEFT JOIN SolarSystems s1 ON j.fromSystemId = s1.solarSystemId 
            LEFT JOIN SolarSystems s2 ON j.toSystemId = s2.solarSystemId 
            WHERE s1.solarSystemId IS NULL OR s2.solarSystemId IS NULL
        """)
        invalid_jumps = cursor.fetchone()[0]
        if invalid_jumps == 0:
            checks.append("✅ All jumps reference valid systems")
        else:
            checks.append(f"❌ {invalid_jumps} jumps reference invalid systems")
    except sqlite3.Error as e:
        checks.append(f"❌ Error checking jump relationships: {e}")
    
    conn.close()
    
    for check in checks:
        print(f"  {check}")

def print_schema(schema, title):
    print(f"\nSchema for {title}:")
    for table, columns in schema.items():
        print(f"Table: {table}")
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")
        print()

def compare_schemas(ref_schema, gen_schema):
    print("\n=== SCHEMA COMPARISON ===")
    schema_issues = []
    
    for table in ref_schema:
        if table not in gen_schema:
            schema_issues.append(f"❌ Missing table in generated DB: {table}")
            continue
            
        ref_cols = dict(ref_schema[table])
        gen_cols = dict(gen_schema[table])
        
        for col, col_type in ref_cols.items():
            if col not in gen_cols:
                schema_issues.append(f"❌ Missing column in table '{table}': {col}")
            elif gen_cols[col].upper() != col_type.upper():
                schema_issues.append(f"❌ Type mismatch in table '{table}', column '{col}': {col_type} (ref) vs {gen_cols[col]} (gen)")
    
    if not schema_issues:
        print("✅ All required tables and columns exist with correct types")
    else:
        for issue in schema_issues:
            print(f"  {issue}")
    
    return len(schema_issues) == 0

def main():
    print("=== DATABASE COMPARISON TOOL ===")
    print(f"Reference DB: {REFERENCE_DB}")
    print(f"Generated DB: {GENERATED_DB}")
    
    # Schema comparison
    ref_schema = get_schema(REFERENCE_DB)
    gen_schema = get_schema(GENERATED_DB)
    
    print_schema(ref_schema, "Reference DB")
    print_schema(gen_schema, "Generated DB")
    
    schema_valid = compare_schemas(ref_schema, gen_schema)
    
    # Data comparison
    ref_counts, gen_counts = compare_data_integrity(REFERENCE_DB, GENERATED_DB)
    
    # Table mapping for data comparison (reference -> generated)
    table_mapping = {
        'Regions': 'Regions',
        'Constellations': 'Constellations', 
        'SolarSystems': 'SolarSystems',
        'Jumps': 'Jumps'
    }
    
    compare_sample_data(REFERENCE_DB, GENERATED_DB, table_mapping)
    
    # Validate relationships in generated database
    validate_data_relationships(GENERATED_DB)
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Schema compatibility: {'✅ PASS' if schema_valid else '❌ FAIL'}")
    
    # Check if generated DB has equal or more records
    data_adequate = all(gen_counts.get(table, 0) >= count for table, count in ref_counts.items())
    print(f"Data coverage: {'✅ ADEQUATE' if data_adequate else '❌ INSUFFICIENT'}")
    
    if schema_valid and data_adequate:
        print("🎉 Generated database is compatible and contains adequate data!")
    else:
        print("⚠️  Issues found - see details above")

if __name__ == "__main__":
    main()
