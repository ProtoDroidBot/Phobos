# Phobos Scripts Reference

Documentation for utility scripts and tools included with Phobos.

## Core Scripts

### run.py

**Main Phobos extraction script** - Extracts EVE client data and outputs JSON files.

**Usage**:
```bash
python run.py --eve <EVE_PATH> --json <OUTPUT_DIR> [OPTIONS]
```

**Required Arguments**:
- `--eve`, `-e` - Path to EVE client folder (e.g., `C:\CCP\EVE Frontier`)
- `--json`, `-j` - Output folder for JSON files

**Optional Arguments**:
- `--server`, `-s` - Server to pull data from (default: `stillness`)
  - Currently only `stillness` (EVE Frontier) is supported
- `--translate`, `-t` - Language for string translation (default: `multi`)
  - Options: `de`, `en-us`, `es`, `fr`, `it`, `ja`, `ko`, `ru`, `zh`, `multi`
  - `multi` mode adds `<field>_<lang>` fields for all languages
  - Single language mode replaces original text in-place
- `--list`, `-l` - Comma-separated list of containers to extract
  - If not specified, extracts everything
  - Example: `"types,industry_blueprints,systems"`
- `--group`, `-g` - Split large containers into multiple files
  - Specify max entries per file (e.g., `1000`)

**Examples**:
```bash
# Extract everything with multi-language translation
python run.py --eve "C:\CCP\EVE Frontier" --json output --translate=multi

# Extract only specific containers
python run.py --eve "C:\CCP\EVE Frontier" --json output --list="types,industry_blueprints,metadata"

# Extract types with English translation only
python run.py --eve "C:\CCP\EVE Frontier" --json output --list="types" --translate=en-us

# Extract types and split into files of 1000 entries
python run.py --eve "C:\CCP\EVE Frontier" --json output --list="types" --group=1000
```

**Output**: Creates `output/<miner_name>/<container_name>.json` files

**See also**: [DATA_CONTAINERS.md](DATA_CONTAINERS.md) for available containers

---

### generate.py

**EVE Universe Database Generator** - Creates normalized SQLite database from Phobos output with systems, constellations, regions, and navigation data.

**Usage**:
```bash
python generate.py --output <DB_FILE> --phobos-output <PHOBOS_DIR>
```

**Required Arguments**:
- `--output`, `-o` - Output SQLite database file path
- `--phobos-output`, `-p` - Path to Phobos output directory

**Examples**:
```bash
# Create universe database from Phobos output
python generate.py --output eve_universe.db --phobos-output ./output

# Using short argument names
python generate.py -o starmap.db -p ./output
```

**Database Schema**:

**Regions** table:
- `regionId` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `centerX`, `centerY`, `centerZ` (REAL) - Region center coordinates

**Constellations** table:
- `constellationId` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `regionId` (INTEGER) - Foreign key to Regions
- `centerX`, `centerY`, `centerZ` (REAL) - Constellation center

**SolarSystems** table:
- `solarSystemId` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `constellationId` (INTEGER) - Foreign key to Constellations
- `regionId` (INTEGER) - Foreign key to Regions
- `x`, `y`, `z` (REAL) - System coordinates
- `security` (REAL) - Security status
- `radius` (REAL) - System radius
- `luminosity` (REAL) - Star luminosity
- `border` (INTEGER) - Border system flag
- `corridor` (INTEGER) - Corridor system flag
- `fringe` (INTEGER) - Fringe system flag
- `hub` (INTEGER) - Hub system flag
- `international` (INTEGER) - International flag
- `regional` (INTEGER) - Regional flag
- `constellation` (INTEGER) - Constellation flag

**Jumps** table:
- `fromSolarSystemId` (INTEGER)
- `toSolarSystemId` (INTEGER)
- PRIMARY KEY on both columns

**Planets** table:
- `planetId` (INTEGER PRIMARY KEY)
- `solarSystemId` (INTEGER)
- `typeId` (INTEGER)
- `x`, `y`, `z` (REAL) - Planet coordinates

**Moons** table:
- `moonId` (INTEGER PRIMARY KEY)
- `planetId` (INTEGER)
- `solarSystemId` (INTEGER)
- `x`, `y`, `z` (REAL) - Moon coordinates

**NpcStations** table:
- `stationId` (INTEGER PRIMARY KEY)
- `solarSystemId` (INTEGER)
- `typeId` (INTEGER)
- `x`, `y`, `z` (REAL) - Station coordinates

**LagrangePoints** table:
- `lagrangePointId` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `solarSystemId` (INTEGER)
- `planetId` (INTEGER)
- `pointType` (TEXT) - L1, L2, L3, L4, L5
- `x`, `y`, `z` (REAL) - Lagrange point coordinates

**Types** table:
- `typeId` (INTEGER PRIMARY KEY)
- `typeName` (TEXT)
- `groupId` (INTEGER)

**Workflow**:
1. First run `run.py` to extract EVE client data
2. Then run `generate.py` to create the database
3. Use the database for navigation, route planning, etc.

**See also**: [DATABASE_GENERATION.md](DATABASE_GENERATION.md) for detailed guide

---

### query_blueprints.py

**Blueprint Query Tool** - Search and display manufacturing schemas/blueprints with material requirements and products.

**Usage**:
```bash
python query_blueprints.py [SEARCH_OPTIONS] [--data-dir DIR]
```

**Search Options** (choose one):
- `--search`, `-s QUERY` - Search blueprints (inputs and outputs)
- `--output`, `-o ITEM` - Find blueprints that produce this item
- `--input`, `-i MATERIAL` - Find blueprints that use this material
- `--id ID` - Get specific blueprint by ID

**Modifiers**:
- `--exact`, `-e` - Require exact name match (default: partial match)
- `--verbose`, `-v` - Show additional details (categories, etc.)
- `--limit`, `-l N` - Limit number of results shown
- `--data-dir DIR` - Path to Phobos output directory (default: `output`)

**Examples**:
```bash
# Search for ammo blueprints
python query_blueprints.py --output "ammo"

# Find blueprints using iron
python query_blueprints.py --input "iron" --verbose

# Search everywhere for gyrojet
python query_blueprints.py --search "gyrojet"

# Get specific blueprint by ID
python query_blueprints.py --id 1010

# Exact match for "Leap" blueprint
python query_blueprints.py --output "Leap" --exact

# Find blueprints using palladium, show first 5
python query_blueprints.py --input "palladium" --limit 5 --verbose
```

**Output Format**:
```
======================================================================
Blueprint ID: 1010
Product: AC Gyrojet Ammo 1 (S)
Run Time: 2s

Inputs:
  • Iron-Rich Nodules                            24

Outputs:
  • AC Gyrojet Ammo 1 (S)                       100
======================================================================
```

**Programmatic Usage**:
```python
from query_blueprints import BlueprintDB

db = BlueprintDB("output")

# Find blueprints by output
results = db.find_blueprints_by_output("ammo")

# Find blueprints by input
results = db.find_blueprints_by_input("iron")

# Get blueprint by ID
bp = db.get_blueprint(1010)

# Print formatted
for result in results:
    db.print_blueprint(result, verbose=True)
```

**See also**: [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md) for detailed guide

---

## Test/Utility Scripts

### compare_db_schema.py

**Database Schema Comparison Tool** - Compares structure and data between two SQLite databases.

**Purpose**: Validate generated databases against reference databases

**Configuration** (edit file):
```python
REFERENCE_DB = r"path/to/reference.db"
GENERATED_DB = r"path/to/generated.db"
```

**Usage**:
```bash
python compare_db_schema.py
```

**Output**:
- Schema comparison (tables, columns, types)
- Data integrity comparison (record counts)
- Sample data comparison
- Missing/extra tables and columns

**Use Cases**:
- Validate `generate.py` output
- Detect schema changes between EVE versions
- Ensure data migration completeness

---

### test_names.py

**Name Localization Tester** - Verifies that localized names are properly applied to database records.

**Purpose**: Test that translation is working correctly for systems, regions, constellations

**Database**: Expects `eve_universe.db` in current directory

**Usage**:
```bash
python test_names.py
```

**Output**:
```
Found system 30009299: ID=30009299, Name="I4F-MCH"
Found I4F-MCH: (30009299, 'I4F-MCH', 20000123)

Sample systems with localized names:
  30000001: Tanoo
  30000002: Akora
  ...

Systems with real names: 5234 out of 8000
```

**Checks**:
- Specific system lookups
- Name vs ID resolution
- Localization coverage statistics
- Sample data verification

---

### test_lpoints.py

**Lagrange Points Extraction Test** - Verifies Lagrange point data extraction from solar system content.

**Purpose**: Test parsing of complex nested FSD data structures

**Data Source**: `output/fsd_binary_schema/solarsystemcontent.json`

**Usage**:
```bash
python test_lpoints.py
```

**Output**:
```
Found 847 Lagrange Points in first 100 systems

Sample L-Points:
  System 30000001, Planet 40000123, L1: (1.23e+11, 4.56e+10, 7.89e+09)
  System 30000001, Planet 40000123, L2: (-1.23e+11, -4.56e+10, -7.89e+09)
  ...
```

**Use Cases**:
- Debug FSD schema parsing
- Validate planet/moon data extraction
- Test coordinate conversion

---

### scripts/itemdiff.py

**Item/Type Difference Analyzer** - Compares EVE type data between different client versions or exports.

**Purpose**: Track changes to items, attributes, blueprints between patches

**Usage**:
```bash
python scripts/itemdiff.py [OPTIONS] old_export/ new_export/
```

**Features**:
- Detects added, removed, changed types
- Compares attributes, effects, materials
- Tracks publication status changes
- Market group changes
- Blueprint material changes

**Output**:
- Added items
- Removed items
- Changed items with diffs
- Statistical summary

**Configuration Options** (in script):
- `process_pub` - Track publication status changes
- `process_mkt` - Track market group changes
- `process_attrs` - Compare attributes
- `process_effects` - Compare effects
- `process_mats` - Compare materials/blueprints

---

## SQL Scripts

### sql/create_types_table.sql

**Types Table Schema** - SQL schema for creating a types lookup table.

**Purpose**: Fast type ID to name lookups and type queries

**Usage**:
```bash
sqlite3 your_database.db < sql/create_types_table.sql
```

**Schema**:
```sql
CREATE TABLE types (
    typeID INTEGER PRIMARY KEY,
    typeName TEXT NOT NULL,
    groupID INTEGER,
    description TEXT,
    published INTEGER,
    mass REAL,
    volume REAL,
    capacity REAL,
    portionSize INTEGER,
    basePrice REAL,
    marketGroupID INTEGER,
    iconID INTEGER,
    soundID INTEGER,
    graphicID INTEGER
);
```

**Indexes**:
- `idx_types_name` - Name lookups
- `idx_types_groupID` - Group filtering
- `idx_types_marketGroupID` - Market items

**Example Queries**:
```sql
-- Lookup by ID
SELECT typeName FROM types WHERE typeID = 34;

-- Find by name
SELECT typeID, typeName FROM types WHERE typeName LIKE '%Tritanium%';

-- Published types in group
SELECT typeID, typeName FROM types WHERE groupID = 18 AND published = 1;
```

---

### sql/validate_systems.sql

**System Name Pattern Validator** - SQL query to validate and classify solar system names.

**Purpose**: Verify system name formats and identify anomalies

**Usage**:
```bash
sqlite3 eve_universe.db < sql/validate_systems.sql
```

**Validation Patterns**:
- `[AMU] [0-9]{3,4}` - Black holes (A 123, M 456, U 789)
- `[A-Z0-9]{3}-[A-Z0-9]{3}` - Nullsec format (I4F-MCH)
- `[A-Z0-9]:[A-Z0-9]{4}` - Colon format (J:1234)
- `[A-Z0-9].[A-Z0-9]{3}.[A-Z0-9]{3}` - Dot format (A.BC.DEF)
- `[A-Z0-9]{3}|[A-Z0-9]{3}` - Pipe format (ABC|DEF)
- `[A-Z][a-z]+` - Proper nouns (Jita, Amarr)
- `AD[0-9]{3}` - AD prefix (AD123)
- `V-[0-9]{3}` - V prefix (V-001)

**Output**:
1. Systems that don't match any pattern
2. Count breakdown by pattern type
3. Unclassified system count

**Use Cases**:
- Data quality assurance
- Identify malformed names
- Classification statistics

---

## Best Practices

### Running the Full Pipeline

```bash
# 1. Extract EVE client data
python run.py --eve "C:\CCP\EVE Frontier" --json output --translate=multi

# 2. Generate universe database
python generate.py --output eve_universe.db --phobos-output ./output

# 3. Validate the database
python test_names.py

# 4. Query blueprints
python query_blueprints.py --search "ammo" --verbose
```

### Performance Tips

- Use `--list` to extract only needed containers
- Use `--group` for very large datasets
- Single language translation is faster than `multi`
- Generate database on SSD for faster writes
- Index SQLite database after bulk inserts

### Data Quality Checks

```bash
# Check Lagrange points extraction
python test_lpoints.py

# Validate localization
python test_names.py

# Compare against reference database
python compare_db_schema.py
```

---

### generate_image_zip.py

**Icon Extractor** - Extracts item icons from the EVE client resource files and packages them into a ZIP archive.

**Usage**:
```bash
python generate_image_zip.py --eve <EVE_PATH> [OPTIONS]
```

**Required Arguments**:
- `--eve` - Path to EVE client installation directory

**Optional Arguments**:
- `--server` - Server alias (default: `stillness`)
- `--output` - Path to Phobos output directory containing types.json (default: `output`)
- `--zip` - Output ZIP file path (default: `output/zip/item_icons.zip`)
- `--verbose` - Enable verbose progress output

**Features**:
- Filters for published items with mass > 0
- Prioritizes high-resolution renders (512px) for ships and structures
- Falls back to standard UI icons (64px) if high-res not available
- Handles both PNG and JPG source formats (converts to PNG in zip)

**Examples**:
```bash
# Extract icons from EVE Frontier
python generate_image_zip.py --eve "C:\CCP\EVE Frontier"

# Extract from EVE Online with custom output
python generate_image_zip.py --eve "C:\CCP\EVE Online" --server tq --zip icons.zip
```

---

### tools/tidy_outputs.py

**JSON Output Cleaner** - Optimizes Phobos JSON output by removing redundant data.

**Usage**:
```bash
python tools/tidy_outputs.py [OPTIONS]
```

**Optional Arguments**:
- `--input`, `-i` - Input directory (default: `output`)
- `--output`, `-o` - Output directory (default: `output_cleaned`)
- `--dry-run` - Report changes without writing files
- `--min-count` - Minimum entries to analyze (default: 2)
- `--max-size-mb` - Skip files larger than size (default: 50)

**Optimization Strategy**:
- Removes keys that have the exact same value across ALL entries in a file (Constant Keys)
- Removes duplicate keys where Key A always equals Key B (Redundant Keys)
- Preserves file structure

**Examples**:
```bash
# Clean output directory
python tools/tidy_outputs.py

# Dry run to see what would be removed
python tools/tidy_outputs.py --dry-run
```

## See Also

- [DATA_CONTAINERS.md](DATA_CONTAINERS.md) - Available data containers
- [DATABASE_GENERATION.md](DATABASE_GENERATION.md) - Database creation guide
- [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md) - Blueprint queries
- Main [README.md](../README.md) - Project overview
