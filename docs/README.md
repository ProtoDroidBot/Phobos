# Phobos Documentation

Complete documentation for the Phobos EVE data extraction toolkit.

## 📚 Documentation Files

### [DATA_CONTAINERS.md](DATA_CONTAINERS.md)
**Complete data container reference** - 304 lines

Comprehensive guide to all 113+ data containers available from Phobos extraction:
- Overview of 6 miners (fsd_built, fsd_lite, sqlite, phobos, resource_pickle, fsd_binary_schema)
- Detailed structure for key containers (types, blueprints, attributes, etc.)
- Language support and multi-language translation
- Container filtering and output grouping
- Data normalization reference

**Use this when**: You need to know what data is available or understand container structure

---

### [SCRIPTS_REFERENCE.md](SCRIPTS_REFERENCE.md)
**Script and tool documentation** - 365 lines

Documentation for all Phobos scripts and utilities:
- **run.py** - Main extraction script with all CLI options
- **generate.py** - Universe database generator
- **query_blueprints.py** - Blueprint query tool
- **Test scripts** - compare_db_schema.py, test_names.py, test_lpoints.py
- **SQL utilities** - Schema templates and validators

Includes usage examples, command-line options, and best practices.

**Use this when**: You need to run scripts or understand their functionality

---

### [DATABASE_GENERATION.md](DATABASE_GENERATION.md)
**Database creation and query guide** - 567 lines

Step-by-step guide to creating and querying the EVE universe SQLite database:
- Quick start guide
- Complete schema documentation (8 tables)
- Example queries for common tasks
- Advanced queries (route planning, spatial searches)
- Performance optimization
- Integration examples (Python, JavaScript, Rust)

**Use this when**: Building navigation tools, map generators, or universe analysis applications

---

### [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md)
**Blueprint search tool guide** - 112 lines

Guide to the `query_blueprints.py` tool for manufacturing schema queries:
- Search by product, material, or everywhere
- Command-line examples
- Programmatic API usage
- Output format reference

**Use this when**: Looking for manufacturing recipes or analyzing production chains

---

## 🚀 Quick Start

### 1. Extract EVE Client Data
```bash
python run.py --eve "C:\CCP\EVE Frontier" --json output --translate=multi
```
See: [SCRIPTS_REFERENCE.md § run.py](SCRIPTS_REFERENCE.md#runpy)

### 2. Query Blueprints
```bash
python query_blueprints.py --search "ammo" --verbose
```
See: [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md)

### 3. Generate Universe Database
```bash
python generate.py --output eve_universe.db --phobos-output ./output
```
See: [DATABASE_GENERATION.md § Quick Start](DATABASE_GENERATION.md#quick-start)

---

## 📖 Common Tasks

### Finding Available Data
**Question**: What data can I extract from the EVE client?

**Answer**: See [DATA_CONTAINERS.md § Overview](DATA_CONTAINERS.md#overview) for a complete list of 113+ containers across 6 miners.

**Popular containers**:
- `types.json` - All items with names, descriptions, stats
- `industry_blueprints.json` - Manufacturing schemas
- `systems.json`, `regions.json`, `jumps.json` - Universe navigation data
- `dogmaattributes.json`, `dogmaeffects.json` - Game mechanics
- `localization_*.json` - Multi-language translations

---

### Extracting Specific Data
**Question**: How do I extract only specific containers?

**Answer**: Use the `--list` argument with `run.py`:
```bash
python run.py --eve "..." --json output --list="types,industry_blueprints,systems"
```

See: [SCRIPTS_REFERENCE.md § run.py](SCRIPTS_REFERENCE.md#runpy)

---

### Querying Blueprints
**Question**: How do I find manufacturing recipes?

**Answer**: Use the `query_blueprints.py` tool:
```bash
# Find what produces an item
python query_blueprints.py --output "ammo"

# Find what uses a material
python query_blueprints.py --input "iron" --verbose

# Search everywhere
python query_blueprints.py --search "gyrojet"
```

See: [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md)

---

### Building Navigation Tools
**Question**: How do I create a route planner or map tool?

**Answer**: Generate the universe database and query it:

1. **Extract universe data**:
   ```bash
   python run.py --eve "..." --json output --list="systems,regions,jumps,solarsystemcontent"
   ```

2. **Generate database**:
   ```bash
   python generate.py --output starmap.db --phobos-output ./output
   ```

3. **Query for routes** (example):
   ```sql
   -- Find connected systems
   SELECT s.name
   FROM Jumps j
   JOIN SolarSystems s ON j.toSolarSystemId = s.solarSystemId
   WHERE j.fromSolarSystemId = 30000142;
   ```

See: [DATABASE_GENERATION.md](DATABASE_GENERATION.md)

---

### Understanding Type Data
**Question**: What information is available about items/types?

**Answer**: The `types.json` container includes:
- Type ID and name (multi-language)
- Group and category classification
- Physical properties (mass, volume, capacity)
- Market data (price, market group)
- Description text

Structure example:
```json
{
  "34": {
    "typeID": 34,
    "typeName_en-us": "Tritanium",
    "groupID": 18,
    "mass": 1.0,
    "volume": 0.01,
    "basePrice": 5.0
  }
}
```

See: [DATA_CONTAINERS.md § types.json](DATA_CONTAINERS.md#typesjson)

---

### Multi-Language Support
**Question**: How do I get localized names in different languages?

**Answer**: Use `--translate=multi` (default) when running extraction:
```bash
python run.py --eve "..." --json output --translate=multi
```

This adds fields like:
- `typeName_en-us` (English)
- `typeName_de` (German)
- `typeName_ja` (Japanese)
- etc.

See: [DATA_CONTAINERS.md § Language Support](DATA_CONTAINERS.md#language-support)

---

### Database Queries
**Question**: What SQL queries can I run on the universe database?

**Answer**: The database supports:
- System/region/constellation lookups
- Jump gate navigation queries
- Distance calculations
- Route planning (with recursive CTEs)
- Spatial searches
- Planetary data queries

Example queries:
```sql
-- Find a system
SELECT * FROM SolarSystems WHERE name = 'Jita';

-- Get connected systems
SELECT s.name
FROM Jumps j
JOIN SolarSystems s ON j.toSolarSystemId = s.solarSystemId
WHERE j.fromSolarSystemId = 30000142;

-- Calculate distance
SELECT SQRT(POWER(a.centerX-b.centerX,2) + POWER(a.centerY-b.centerY,2) + POWER(a.centerZ-b.centerZ,2))
FROM SolarSystems a, SolarSystems b
WHERE a.name = 'Jita' AND b.name = 'Amarr';
```

See: [DATABASE_GENERATION.md § Advanced Queries](DATABASE_GENERATION.md#advanced-queries)

---

## 🔍 Index by Topic

### Data Extraction
- [run.py documentation](SCRIPTS_REFERENCE.md#runpy)
- [Available containers](DATA_CONTAINERS.md#overview)
- [Container filtering](DATA_CONTAINERS.md#container-filtering)
- [Output grouping](DATA_CONTAINERS.md#output-grouping)

### Manufacturing/Blueprints
- [Blueprint query tool](BLUEPRINT_QUERY_GUIDE.md)
- [industry_blueprints.json structure](DATA_CONTAINERS.md#industry_blueprintsjson)
- [Query examples](BLUEPRINT_QUERY_GUIDE.md#example-queries)

### Universe/Navigation
- [Database generation](DATABASE_GENERATION.md#quick-start)
- [Systems/regions/jumps data](DATA_CONTAINERS.md#miner-fsd_binary_schema)
- [Route planning queries](DATABASE_GENERATION.md#route-planning)
- [Spatial queries](DATABASE_GENERATION.md#spatial-queries)

### Type/Item Data
- [types.json structure](DATA_CONTAINERS.md#typesjson)
- [groups.json structure](DATA_CONTAINERS.md#groupsjson)
- [categories.json structure](DATA_CONTAINERS.md#categoriesjson)
- [Type attributes](DATA_CONTAINERS.md#dogmaattributesjson)

### Localization
- [Multi-language translation](DATA_CONTAINERS.md#language-support)
- [Localization containers](DATA_CONTAINERS.md#miner-resource_pickle)
- [Translation modes](SCRIPTS_REFERENCE.md#runpy)

### Database Operations
- [Schema reference](DATABASE_GENERATION.md#database-schema)
- [Example queries](DATABASE_GENERATION.md#advanced-queries)
- [Performance optimization](DATABASE_GENERATION.md#performance-optimization)
- [Integration examples](DATABASE_GENERATION.md#integration-examples)

### Testing/Validation
- [test_names.py](SCRIPTS_REFERENCE.md#test_namespy)
- [test_lpoints.py](SCRIPTS_REFERENCE.md#test_lpointspy)
- [compare_db_schema.py](SCRIPTS_REFERENCE.md#compare_db_schemapy)
- [SQL validation](SCRIPTS_REFERENCE.md#sqlvalidate_systemssql)

---

## 📦 File Sizes

| File | Size | Lines | Purpose |
|------|------|-------|---------|
| DATA_CONTAINERS.md | 10.1 KB | 304 | Container reference |
| SCRIPTS_REFERENCE.md | 12.9 KB | 365 | Script documentation |
| DATABASE_GENERATION.md | 16.3 KB | 567 | Database guide |
| BLUEPRINT_QUERY_GUIDE.md | 3.6 KB | 112 | Blueprint queries |
| **Total** | **43.0 KB** | **1348** | Complete documentation |

---

## 🔗 External Resources

- [Main README](../README.md) - Project overview and setup
- [GitHub Repository](https://github.com/eve-frontier/Phobos) - Source code
- `.github/copilot-instructions.md` - AI assistant context

---

## 💡 Contributing to Documentation

When adding new features:
1. Document new containers in [DATA_CONTAINERS.md](DATA_CONTAINERS.md)
2. Document new scripts in [SCRIPTS_REFERENCE.md](SCRIPTS_REFERENCE.md)
3. Add database schema changes to [DATABASE_GENERATION.md](DATABASE_GENERATION.md)
4. Update this README index as needed

Keep documentation:
- **Concrete**: Include real examples and file paths
- **Concise**: Use tables and code blocks
- **Complete**: Cover all common use cases
- **Current**: Update when code changes

---

*Last updated: January 2026*
