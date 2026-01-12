# Blueprint Query Guide

## Overview

Blueprint data has been identified in the Phobos exports at:
- **Blueprint data**: `output/fsd_built/industry_blueprints.json`
- **Type names**: `output/fsd_built/types.json`
- **Group/categories**: `output/fsd_built/groups.json`

A new query tool `query_blueprints.py` has been created to easily search and display blueprint information.

## Blueprint Data Structure

Each blueprint contains:
- **blueprintID**: Unique identifier for the blueprint/schema
- **inputs**: Array of materials required (typeID + quantity)
- **outputs**: Array of products produced (typeID + quantity)
- **primaryTypeID**: The main product type ID
- **runTime**: Manufacturing time in seconds

## Using the Query Tool

### Basic Searches

Search for blueprints by product name:
```bash
python query_blueprints.py --output "ammo"
python query_blueprints.py -o "gyrojet"
```

Search for blueprints by input material:
```bash
python query_blueprints.py --input "iron"
python query_blueprints.py -i "palladium"
```

Search everywhere (inputs + outputs):
```bash
python query_blueprints.py --search "gyrojet"
python query_blueprints.py -s "autocannon"
```

### Advanced Options

Get specific blueprint by ID:
```bash
python query_blueprints.py --id 1010
```

Require exact name match:
```bash
python query_blueprints.py --output "Leap" --exact
```

Show verbose details (categories):
```bash
python query_blueprints.py --output "ammo" --verbose
python query_blueprints.py -o "ammo" -v
```

Limit number of results:
```bash
python query_blueprints.py --search "ammo" --limit 5
python query_blueprints.py -s "ammo" -l 5
```

## Example Queries

### Find AC Gyrojet Ammo blueprints
```bash
python query_blueprints.py --output "ac gyrojet ammo"
```

Output:
```
Blueprint ID: 1010
Product: AC Gyrojet Ammo 1 (S)
Run Time: 2s

Inputs:
  • Iron-Rich Nodules                            24

Outputs:
  • AC Gyrojet Ammo 1 (S)                       100
```

### Find blueprints using Palladium
```bash
python query_blueprints.py --input "palladium" --verbose --limit 3
```

### Find Heat Exchanger blueprints
```bash
python query_blueprints.py --output "heat exchanger"
```

### Find Protocol Frame blueprints
```bash
python query_blueprints.py --output "protocol frame" --verbose
```

## Database Stats

Current export contains:
- **211 blueprints** (manufacturing schemas/reactions)
- **32,193 types** (items, materials, products)
- **1,602 groups** (categories)

## Programmatic Usage

You can also use the `BlueprintDB` class in your own Python scripts:

```python
from query_blueprints import BlueprintDB

# Initialize
db = BlueprintDB("output")

# Find blueprints producing specific item
results = db.find_blueprints_by_output("ammo")

# Find blueprints using specific material
results = db.find_blueprints_by_input("iron")

# Get blueprint by ID
bp = db.get_blueprint(1010)

# Print formatted output
for result in results:
    db.print_blueprint(result, verbose=True)

# Get type name
name = db.get_type_name(88561)

# Get category
category = db.get_type_category(88561)
```

## Data Mapping

The tool automatically resolves:
- **Type IDs → Names**: Uses `types.json` with multi-language support
- **Group IDs → Categories**: Uses `groups.json` for categorization
- **Run Times**: Formats seconds into human-readable time (2m 36s, etc.)

## Notes

- All searches are case-insensitive by default
- Partial matches are supported unless `--exact` is specified
- Run times match the in-game schema display format
- Material quantities and outputs match game data exactly
