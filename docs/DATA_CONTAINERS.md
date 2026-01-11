# Phobos Data Containers Reference

This document describes all data containers available from the Phobos extraction process and their contents.

## Overview

Phobos organizes extracted EVE client data into **miners** (data sources) that each produce multiple **containers** (output files). Each container represents a specific data table or collection.

Current statistics (as of extraction):
- **fsd_built**: 83 containers - Core game data from binary FSD format
- **fsd_lite**: 10 containers - Lightweight SQLite-backed FSD data
- **sqlite**: 2 containers - Direct SQLite database tables
- **phobos**: 1 container - Metadata about the extraction
- **resource_pickle**: 13 containers - Localization and resource data
- **fsd_binary_schema**: 14 containers - Diagnostic schema inspection

Output location: `output/<miner_name>/<container_name>.json`

## Miner: fsd_built

**Source**: Binary FSD format via dynamic loaders (`app:/bin64/*Loader.pyd`)  
**Path**: `output/fsd_built/`  
**Container count**: 83

Core game data including types, groups, blueprints, attributes, and more.

### Key Containers

#### industry_blueprints.json
Manufacturing schemas/blueprints for all craftable items.

**Structure**:
```json
{
  "blueprintID": {
    "inputs": [
      {"typeID": 12345, "quantity": 10}
    ],
    "outputs": [
      {"typeID": 67890, "quantity": 1}
    ],
    "primaryTypeID": 67890,
    "runTime": 120
  }
}
```

**Fields**:
- `blueprintID`: Unique identifier for blueprint/schema
- `inputs`: Array of materials required (typeID + quantity)
- `outputs`: Array of products produced (typeID + quantity)
- `primaryTypeID`: Main product type ID
- `runTime`: Manufacturing time in seconds

**See also**: [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md) for query tool

#### types.json
Complete item/type database with names, attributes, and metadata.

**Structure**:
```json
{
  "typeID": {
    "typeID": 34,
    "typeName_en-us": "Tritanium",
    "groupID": 18,
    "categoryID": 4,
    "description_en-us": "Base mineral...",
    "mass": 1.0,
    "volume": 0.01,
    "capacity": 0.0,
    "published": 1,
    "marketGroupID": 1234,
    "basePrice": 5.0
  }
}
```

**Fields**:
- `typeID`: Unique identifier for item type
- `typeName_<lang>`: Localized item name (multi-language)
- `groupID`: Type group classification
- `categoryID`: High-level category
- `description_<lang>`: Localized description
- `mass`, `volume`, `capacity`: Physical properties
- `published`: Whether visible in game (0/1)
- `marketGroupID`: Market category (null if not tradeable)
- `basePrice`: NPC base price

#### groups.json
Type group classifications (weapons, minerals, ships, etc.)

**Structure**:
```json
{
  "groupID": {
    "groupID": 18,
    "groupName_en-us": "Mineral",
    "categoryID": 4,
    "published": 1,
    "anchorable": 0,
    "anchored": 0,
    "fittableNonSingleton": 0
  }
}
```

#### categories.json
Top-level type classifications

**Structure**:
```json
{
  "categoryID": {
    "categoryID": 4,
    "categoryName_en-us": "Material",
    "published": 1
  }
}
```

#### dogmaattributes.json
Attribute definitions (damage, range, speed, etc.)

**Structure**:
```json
{
  "attributeID": {
    "attributeID": 6,
    "attributeName": "damage",
    "displayName_en-us": "Damage",
    "description_en-us": "...",
    "defaultValue": 0.0,
    "published": 1,
    "unitID": 1,
    "highIsGood": 1,
    "stackable": 1
  }
}
```

#### dogmaeffects.json
Effect definitions (cloaking, repair, warp drive, etc.)

#### marketgroups.json
Market category hierarchy

**Structure**:
```json
{
  "marketGroupID": {
    "marketGroupID": 1234,
    "marketGroupName_en-us": "Ammunition & Charges",
    "parentGroupID": 100,
    "hasTypes": 1,
    "iconID": 1234
  }
}
```

#### factions.json
NPC faction data

#### regions.json, constellations.json, systems.json
(Note: For EVE Frontier, use `fsd_binary_schema` versions instead)

#### Other Notable Containers

- `ancestries.json` - Character ancestry data
- `bloodlines.json` - Character bloodline data
- `billboards.json` - In-game billboard/sign data
- `graphicids.json`, `iconids.json` - Visual asset references
- `industry_facilities.json` - Manufacturing facility data
- `metagroups.json` - Meta-level classifications
- `skilltags.json` - Skill categorization
- `traits.json` - Type trait descriptions

## Miner: fsd_binary_schema

**Source**: Binary FSD format with schema diagnostics  
**Path**: `output/fsd_binary_schema/`  
**Container count**: 14

Experimental/diagnostic containers that preserve full loader object structure. **Primary source for EVE Frontier universe data**.

### Key Containers

#### systems.json
Solar system definitions with IDs and basic properties

**Note**: For EVE Frontier, this is the authoritative source for system data.

#### constellations.json
Constellation groupings of solar systems

#### regions.json
Region groupings of constellations

#### jumps.json
Stargate connections between systems

**Structure** (example):
```json
[
  {
    "fromSolarSystemID": "30000001",
    "toSolarSystemID": "30000002"
  }
]
```

#### solarsystemcontent.json
Detailed solar system content including planets, moons, asteroid belts, and Lagrange points

**Structure** (simplified):
```json
{
  "systemID": {
    "planets": {
      "planetID": {
        "position": [x, y, z],
        "lagrangePoints": {
          "L1": [schema, x, y, z],
          "L2": [schema, x, y, z]
        }
      }
    }
  }
}
```

**See also**: Scripts `generate.py`, `test_lpoints.py` for working with this data

#### Other Containers

- `eventtypes.json` - Event type definitions
- `landmarks.json` - Notable location markers
- `locationcache.json` - Cached location data
- `dialogs.json` - Dialog/conversation data
- `triggertypes.json` - Trigger condition types
- `wrecks.json` - Wreck/salvage data
- `factionsowningsolarsystems.json` - Faction sovereignty
- `selectiongroups.json` - UI selection groupings
- `skilltags.json` - Skill tag classifications

## Miner: fsd_lite

**Source**: SQLite-backed FSD format  
**Path**: `output/fsd_lite/`  
**Container count**: 10

Lightweight cache format for frequently accessed data.

### Containers

- `agents.json` - NPC agent data
- `characters.json` - Character information
- `graphics.json` - Graphic definitions
- `sounds.json` - Sound effect references
- `typeattributes.json` - Type-specific attribute values
- `typedogma.json` - Type Dogma data (attributes + effects)
- `typeeffects.json` - Type-specific effect applications
- `typematerials.json` - Reprocessing/material data
- `corporationactivities.json` - Corporation activity types
- `researchagents.json` - Research agent data

## Miner: sqlite

**Source**: Direct SQLite database tables from EVE client  
**Path**: `output/sqlite/`  
**Container count**: 2

Raw SQLite table exports.

### Containers

- `bulkdata_dgmoperands_operandID.json` - Dogma operands table
- `bulkdata_phbtraits_traitID.json` - Traits database table

## Miner: phobos

**Source**: Phobos metadata generator  
**Path**: `output/phobos/`  
**Container count**: 1

### metadata.json
Information about the extraction process

**Structure**:
```json
{
  "clientBuild": "2024567",
  "extractionTime": "2026-01-11T12:34:56Z",
  "server": "stillness"
}
```

## Miner: resource_pickle

**Source**: Pickled Python objects from client resources  
**Path**: `output/resource_pickle/`  
**Container count**: 13

Localization and resource data stored as Python pickles.

### Containers

Localization files by language:
- `localization_en-us.json` - English (US) strings
- `localization_de.json` - German strings
- `localization_es.json` - Spanish strings
- `localization_fr.json` - French strings
- `localization_it.json` - Italian strings
- `localization_ja.json` - Japanese strings
- `localization_ko.json` - Korean strings
- `localization_ru.json` - Russian strings
- `localization_zh.json` - Chinese strings

Additional resource files:
- `localizationmetadata.json` - Localization metadata
- `localizationsettings.json` - Localization configuration
- `resourcecache.json` - Resource cache data
- `texturecomposites.json` - Texture composite definitions

## Language Support

All localized fields use the format `<fieldName>_<lang>` where language codes are:
- `en-us` - English (United States)
- `de` - German (Deutsch)
- `es` - Spanish (Español)
- `fr` - French (Français)
- `it` - Italian (Italiano)
- `ja` - Japanese (日本語)
- `ko` - Korean (한국어)
- `ru` - Russian (Русский)
- `zh` - Chinese (中文)

## Container Filtering

You can extract specific containers using the `--list` argument:

```bash
# Extract only types and blueprints
python run.py --eve "C:\EVE" --json output --list="types,industry_blueprints"

# Extract metadata and traits
python run.py --eve "C:\EVE" --json output --list="metadata,traits"

# Extract all universe data for EVE Frontier
python run.py --eve "C:\EVE" --json output --list="systems,constellations,regions,jumps,solarsystemcontent"
```

## Output Grouping

For large containers, use `--group` to split output into multiple files:

```bash
# Split types.json into files with max 1000 entries each
python run.py --eve "C:\EVE" --json output --list="types" --group 1000
```

This creates files like:
- `types_000000.json`
- `types_000001.json`
- etc.

## Data Normalization

All output is normalized to pure Python primitives:
- EVE FSD objects → Python `dict`
- EVE iterators → Python `list`
- Numeric types → `int`, `float`
- Strings → `str`
- Booleans → `bool`
- Null/None → `null`

This ensures JSON compatibility and easy consumption in any programming language.

## See Also

- [BLUEPRINT_QUERY_GUIDE.md](BLUEPRINT_QUERY_GUIDE.md) - Blueprint query tool
- [SCRIPTS_REFERENCE.md](SCRIPTS_REFERENCE.md) - Utility scripts documentation
- [DATABASE_GENERATION.md](DATABASE_GENERATION.md) - SQLite database creation guide
- Main [README.md](../README.md) - Project overview
