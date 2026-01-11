# EVE Universe Database Generation Guide

Comprehensive guide to generating and using the EVE universe SQLite database from Phobos output.

## Overview

The `generate.py` script transforms Phobos JSON output into a normalized, queryable SQLite database containing:
- Solar systems, constellations, regions
- Jump gate connections
- Planets, moons, stations
- Lagrange points
- Type definitions

This database is optimized for:
- Navigation and route planning
- Universe exploration tools
- Spatial queries
- Map generation
- Data analysis

## Quick Start

```bash
# Step 1: Extract EVE client data with Phobos
python run.py --eve "C:\CCP\EVE Frontier" --json output --translate=multi

# Step 2: Generate universe database
python generate.py --output eve_universe.db --phobos-output ./output

# Step 3: Verify the database
python test_names.py
```

That's it! You now have a complete queryable EVE universe database.

## Requirements

- Phobos output directory (from `run.py`)
- Python 3.7+ (no additional dependencies)
- ~500MB disk space for full database

## Database Schema

### Regions Table

Top-level universe divisions (e.g., Genesis, Heimatar, EVE Frontier regions)

```sql
CREATE TABLE Regions (
    regionId INTEGER PRIMARY KEY,
    name TEXT,
    centerX REAL,
    centerY REAL,
    centerZ REAL
);
```

**Fields**:
- `regionId` - Unique region identifier
- `name` - Localized region name
- `centerX`, `centerY`, `centerZ` - Region center coordinates (meters)

**Example Query**:
```sql
-- Get all regions
SELECT regionId, name FROM Regions ORDER BY name;

-- Find region by name
SELECT * FROM Regions WHERE name = 'Genesis';
```

---

### Constellations Table

Mid-level grouping of solar systems within regions

```sql
CREATE TABLE Constellations (
    constellationId INTEGER PRIMARY KEY,
    name TEXT,
    regionId INTEGER,
    centerX REAL,
    centerY REAL,
    centerZ REAL,
    FOREIGN KEY (regionId) REFERENCES Regions(regionId)
);
```

**Fields**:
- `constellationId` - Unique constellation identifier
- `name` - Localized constellation name
- `regionId` - Parent region ID
- `centerX`, `centerY`, `centerZ` - Constellation center coordinates

**Example Query**:
```sql
-- Get constellations in a region
SELECT c.name, c.constellationId
FROM Constellations c
WHERE c.regionId = 10000001
ORDER BY c.name;

-- Get constellation with region name
SELECT c.name AS constellation, r.name AS region
FROM Constellations c
JOIN Regions r ON c.regionId = r.regionId
WHERE c.constellationId = 20000001;
```

---

### SolarSystems Table

Individual solar systems (the most important table)

```sql
CREATE TABLE SolarSystems (
    solarSystemId INTEGER PRIMARY KEY,
    name TEXT,
    constellationId INTEGER,
    regionId INTEGER,
    x REAL,
    y REAL,
    z REAL,
    security REAL,
    radius REAL,
    luminosity REAL,
    border INTEGER,
    corridor INTEGER,
    fringe INTEGER,
    hub INTEGER,
    international INTEGER,
    regional INTEGER,
    constellation INTEGER,
    FOREIGN KEY (constellationId) REFERENCES Constellations(constellationId),
    FOREIGN KEY (regionId) REFERENCES Regions(regionId)
);

-- Indexes for common queries
CREATE INDEX idx_systems_name ON SolarSystems(name);
CREATE INDEX idx_systems_constellation ON SolarSystems(constellationId);
CREATE INDEX idx_systems_region ON SolarSystems(regionId);
CREATE INDEX idx_systems_security ON SolarSystems(security);
```

**Fields**:
- `solarSystemId` - Unique system identifier
- `name` - Localized system name (e.g., "Jita", "I4F-MCH")
- `constellationId`, `regionId` - Parent hierarchy
- `x`, `y`, `z` - System coordinates in meters (universe reference frame)
- `security` - Security status (-1.0 to 1.0)
- `radius` - System radius in meters
- `luminosity` - Star luminosity
- Boolean flags: `border`, `corridor`, `fringe`, `hub`, `international`, `regional`, `constellation`

**Example Queries**:
```sql
-- Find a system by name
SELECT * FROM SolarSystems WHERE name = 'Jita';

-- Get all systems in a constellation
SELECT solarSystemId, name, security
FROM SolarSystems
WHERE constellationId = 20000001
ORDER BY name;

-- Find high-sec systems
SELECT name, security
FROM SolarSystems
WHERE security >= 0.5
ORDER BY security DESC;

-- Calculate distance between two systems
SELECT 
    a.name AS from_system,
    b.name AS to_system,
    SQRT(
        POWER(a.x - b.x, 2) +
        POWER(a.y - b.y, 2) +
        POWER(a.z - b.z, 2)
    ) / 9460730472580800.0 AS distance_ly
FROM SolarSystems a, SolarSystems b
WHERE a.solarSystemId = 30000142  -- Jita
  AND b.solarSystemId = 30002187; -- Amarr

-- Find nearest systems to a point
SELECT 
    name,
    SQRT(
        POWER(x - 0, 2) +
        POWER(y - 0, 2) +
        POWER(z - 0, 2)
    ) AS distance
FROM SolarSystems
ORDER BY distance
LIMIT 10;
```

---

### Jumps Table

Stargate connections between systems (navigation graph)

```sql
CREATE TABLE Jumps (
    fromSystemId INTEGER NOT NULL,
    toSystemId INTEGER NOT NULL,
    PRIMARY KEY (fromSystemId, toSystemId),
    FOREIGN KEY (fromSystemId) REFERENCES SolarSystems(solarSystemId),
    FOREIGN KEY (toSystemId) REFERENCES SolarSystems(solarSystemId)
);

CREATE INDEX idx_jumps_from ON Jumps(fromSystemId);
CREATE INDEX idx_jumps_to ON Jumps(toSystemId);
```

**Fields**:
- `fromSystemId` - Source system
- `toSystemId` - Destination system

**Note**: Jumps are **bidirectional** but stored once per direction

**Example Queries**:
```sql
-- Get all systems directly connected to Jita
SELECT s.name, s.solarSystemId
FROM Jumps j
JOIN SolarSystems s ON j.toSystemId = s.solarSystemId
WHERE j.fromSystemId = 30000142
ORDER BY s.name;

-- Count connections per system
SELECT 
    s.name,
    COUNT(*) AS connections
FROM Jumps j
JOIN SolarSystems s ON j.fromSystemId = s.solarSystemId
GROUP BY j.fromSystemId
ORDER BY connections DESC
LIMIT 20;

-- Find systems with only one connection (dead ends)
SELECT 
    s.name,
    s.solarSystemId
FROM SolarSystems s
WHERE (
    SELECT COUNT(*)
    FROM Jumps j
    WHERE j.fromSystemId = s.solarSystemId
       OR j.toSystemId = s.solarSystemId
) = 1;

-- Build route (2-hop example)
SELECT 
    s1.name AS start,
    s2.name AS hop1,
    s3.name AS destination
FROM SolarSystems s1
JOIN Jumps j1 ON s1.solarSystemId = j1.fromSystemId
JOIN SolarSystems s2 ON j1.toSystemId = s2.solarSystemId
JOIN Jumps j2 ON s2.solarSystemId = j2.fromSystemId
JOIN SolarSystems s3 ON j2.toSystemId = s3.solarSystemId
WHERE s1.solarSystemId = 30000142  -- Start: Jita
  AND s3.solarSystemId = 30002187  -- End: Amarr
LIMIT 10;
```

---

### Planets Table

Planetary objects within solar systems

```sql
CREATE TABLE Planets (
    planetId INTEGER PRIMARY KEY,
    solarSystemId INTEGER NOT NULL,
    typeId INTEGER,
    x REAL,
    y REAL,
    z REAL,
    FOREIGN KEY (solarSystemId) REFERENCES SolarSystems(solarSystemId)
);

CREATE INDEX idx_planets_system ON Planets(solarSystemId);
```

**Fields**:
- `planetId` - Unique planet identifier
- `solarSystemId` - Parent system
- `typeId` - Planet type ID (references Types table)
- `x`, `y`, `z` - Planet coordinates (system-relative)

**Example Queries**:
```sql
-- Get all planets in a system
SELECT p.planetId, t.typeName
FROM Planets p
LEFT JOIN Types t ON p.typeId = t.typeId
WHERE p.solarSystemId = 30000142;

-- Count planets per system
SELECT 
    s.name,
    COUNT(p.planetId) AS planet_count
FROM SolarSystems s
LEFT JOIN Planets p ON s.solarSystemId = p.solarSystemId
GROUP BY s.solarSystemId
ORDER BY planet_count DESC
LIMIT 20;
```

---

### Moons Table

Moons orbiting planets

```sql
CREATE TABLE Moons (
    moonId INTEGER PRIMARY KEY,
    planetId INTEGER,
    solarSystemId INTEGER NOT NULL,
    x REAL,
    y REAL,
    z REAL,
    FOREIGN KEY (planetId) REFERENCES Planets(planetId),
    FOREIGN KEY (solarSystemId) REFERENCES SolarSystems(solarSystemId)
);

CREATE INDEX idx_moons_planet ON Moons(planetId);
CREATE INDEX idx_moons_system ON Moons(solarSystemId);
```

**Fields**:
- `moonId` - Unique moon identifier
- `planetId` - Parent planet (can be NULL)
- `solarSystemId` - Parent system
- `x`, `y`, `z` - Moon coordinates

**Example Query**:
```sql
-- Get moons for a planet
SELECT moonId FROM Moons WHERE planetId = 40000001;

-- Count moons per system
SELECT 
    s.name,
    COUNT(m.moonId) AS moon_count
FROM SolarSystems s
LEFT JOIN Moons m ON s.solarSystemId = m.solarSystemId
GROUP BY s.solarSystemId
ORDER BY moon_count DESC;
```

---

### NpcStations Table

NPC stations in systems

```sql
CREATE TABLE NpcStations (
    stationId INTEGER PRIMARY KEY,
    solarSystemId INTEGER NOT NULL,
    typeId INTEGER,
    x REAL,
    y REAL,
    z REAL,
    FOREIGN KEY (solarSystemId) REFERENCES SolarSystems(solarSystemId)
);

CREATE INDEX idx_stations_system ON NpcStations(solarSystemId);
```

**Fields**:
- `stationId` - Unique station identifier
- `solarSystemId` - Parent system
- `typeId` - Station type
- `x`, `y`, `z` - Station coordinates

---

### LagrangePoints Table

Lagrange points for planets (gravitational equilibrium points)

```sql
CREATE TABLE LagrangePoints (
    lagrangePointId INTEGER PRIMARY KEY AUTOINCREMENT,
    solarSystemId INTEGER NOT NULL,
    planetId INTEGER,
    pointType TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    FOREIGN KEY (solarSystemId) REFERENCES SolarSystems(solarSystemId),
    FOREIGN KEY (planetId) REFERENCES Planets(planetId)
);

CREATE INDEX idx_lpoints_system ON LagrangePoints(solarSystemId);
CREATE INDEX idx_lpoints_planet ON LagrangePoints(planetId);
```

**Fields**:
- `lagrangePointId` - Auto-incrementing ID
- `solarSystemId` - Parent system
- `planetId` - Parent planet
- `pointType` - L1, L2, L3, L4, or L5
- `x`, `y`, `z` - Point coordinates

**Example Query**:
```sql
-- Get all Lagrange points in a system
SELECT 
    lp.pointType,
    lp.x, lp.y, lp.z,
    t.typeName AS planet_type
FROM LagrangePoints lp
LEFT JOIN Planets p ON lp.planetId = p.planetId
LEFT JOIN Types t ON p.typeId = t.typeId
WHERE lp.solarSystemId = 30000142;

-- Count Lagrange points by type
SELECT pointType, COUNT(*) AS count
FROM LagrangePoints
GROUP BY pointType;
```

---

### Types Table

Type definitions (planets, stations, etc.)

```sql
CREATE TABLE Types (
    typeId INTEGER PRIMARY KEY,
    typeName TEXT,
    groupId INTEGER
);

CREATE INDEX idx_types_name ON Types(typeName);
```

**Fields**:
- `typeId` - Type identifier
- `typeName` - Localized type name
- `groupId` - Type group

**Note**: For complete type data, use `types.json` from Phobos output

---

## Advanced Queries

### Route Planning

```sql
-- Find shortest path using recursive CTE (SQLite 3.8.3+)
WITH RECURSIVE route(system_id, path, hops) AS (
    -- Base case: start system
    SELECT 30000142, '30000142', 0
    
    UNION ALL
    
    -- Recursive case: add connected systems
    SELECT 
        j.toSystemId,
        path || ',' || j.toSystemId,
        hops + 1
    FROM route r
    JOIN Jumps j ON r.system_id = j.fromSystemId
    WHERE hops < 10  -- Max depth
      AND path NOT LIKE '%' || j.toSystemId || '%'  -- Avoid loops
)
SELECT 
    r.hops,
    r.path,
    s.name AS destination
FROM route r
JOIN SolarSystems s ON r.system_id = s.solarSystemId
WHERE r.system_id = 30002187  -- Destination: Amarr
ORDER BY r.hops
LIMIT 1;
```

### Spatial Queries

```sql
-- Find systems within radius of a point
SELECT 
    name,
    x, y, z,
    SQRT(
        POWER(x - target_x, 2) +
        POWER(y - target_y, 2) +
        POWER(z - target_z, 2)
    ) AS distance
FROM SolarSystems
WHERE distance <= 10000000000000000  -- 10 Pm
ORDER BY distance;

-- Find nearest neighbors to a system
SELECT 
    b.name,
    SQRT(
        POWER(a.x - b.x, 2) +
        POWER(a.y - b.y, 2) +
        POWER(a.z - b.z, 2)
    ) / 9460730472580800.0 AS distance_ly
FROM SolarSystems a
CROSS JOIN SolarSystems b
WHERE a.solarSystemId = 30000142  -- Jita
  AND b.solarSystemId != a.solarSystemId
ORDER BY distance_ly
LIMIT 10;
```

### Statistics

```sql
-- Universe statistics
SELECT 
    (SELECT COUNT(*) FROM Regions) AS regions,
    (SELECT COUNT(*) FROM Constellations) AS constellations,
    (SELECT COUNT(*) FROM SolarSystems) AS systems,
    (SELECT COUNT(*) FROM Jumps) AS jumps,
    (SELECT COUNT(*) FROM Planets) AS planets,
    (SELECT COUNT(*) FROM Moons) AS moons,
    (SELECT COUNT(*) FROM LagrangePoints) AS lagrange_points;

-- Security status distribution
SELECT 
    ROUND(security, 1) AS sec_status,
    COUNT(*) AS count
FROM SolarSystems
GROUP BY ROUND(security, 1)
ORDER BY sec_status DESC;
```

## Data Source Files

The generator reads from these Phobos output files:

**Primary Sources** (fsd_binary_schema):
- `systems.json` - System definitions
- `constellations.json` - Constellation definitions
- `regions.json` - Region definitions
- `jumps.json` - Jump connections
- `solarsystemcontent.json` - Planets, moons, stations, Lagrange points

**Fallback Sources** (fsd_built):
- Used if fsd_binary_schema files not available
- Same container names, different structure

**Localization** (resource_pickle):
- `localization_<lang>.json` - Name translations

## Troubleshooting

### Missing Localized Names

**Problem**: Systems show as "System 30000142" instead of "Jita"

**Solution**: Ensure multi-language translation was used:
```bash
python run.py --eve "..." --json output --translate=multi
```

**Verification**:
```bash
python test_names.py
```

### Missing Lagrange Points

**Problem**: LagrangePoints table is empty

**Solution**: Check extraction:
```bash
python test_lpoints.py
```

Ensure `solarsystemcontent.json` exists:
```bash
ls output/fsd_binary_schema/solarsystemcontent.json
```

### Database Validation

**Compare against reference**:
```bash
# Edit compare_db_schema.py with your paths
python compare_db_schema.py
```

**Check record counts**:
```sql
SELECT 
    (SELECT COUNT(*) FROM SolarSystems) AS systems,
    (SELECT COUNT(*) FROM Jumps) AS jumps;
```

Expected ranges (EVE Frontier):
- Systems: 7000-9000
- Jumps: 14000-20000
- Constellations: 1000-1500
- Regions: 80-120

### Performance Optimization

**Create additional indexes**:
```sql
-- Spatial queries
CREATE INDEX idx_systems_xyz ON SolarSystems(x, y, z);

-- Security filtering
CREATE INDEX idx_systems_security ON SolarSystems(security);

-- Composite lookups
CREATE INDEX idx_systems_const_region ON SolarSystems(constellationId, regionId);
```

**Analyze the database**:
```sql
ANALYZE;
```

**Vacuum and optimize**:
```sql
VACUUM;
PRAGMA optimize;
```

## Integration Examples

### Python

```python
import sqlite3

conn = sqlite3.connect('eve_universe.db')
cursor = conn.cursor()

# Get system by name
cursor.execute("SELECT * FROM SolarSystems WHERE name = ?", ("Jita",))
system = cursor.fetchone()

# Get connected systems
cursor.execute("""
    SELECT s.name
    FROM Jumps j
    JOIN SolarSystems s ON j.toSystemId = s.solarSystemId
    WHERE j.fromSystemId = ?
""", (system[0],))
neighbors = cursor.fetchall()

conn.close()
```

### JavaScript/Node.js

```javascript
const sqlite3 = require('sqlite3').verbose();
const db = new sqlite3.Database('eve_universe.db');

db.get("SELECT * FROM SolarSystems WHERE name = ?", ["Jita"], (err, row) => {
    console.log(row);
});

db.close();
```

### Rust

```rust
use rusqlite::{Connection, Result};

fn main() -> Result<()> {
    let conn = Connection::open("eve_universe.db")?;
    
    let mut stmt = conn.prepare("SELECT * FROM SolarSystems WHERE name = ?")?;
    let system = stmt.query_row(["Jita"], |row| {
        Ok((row.get(0)?, row.get(1)?))
    })?;
    
    Ok(())
}
```

## See Also

- [DATA_CONTAINERS.md](DATA_CONTAINERS.md) - Data container reference
- [SCRIPTS_REFERENCE.md](SCRIPTS_REFERENCE.md) - Script documentation
- `sql/create_types_table.sql` - Types table schema
- `sql/validate_systems.sql` - System name validation
- Main [README.md](../README.md) - Project overview
