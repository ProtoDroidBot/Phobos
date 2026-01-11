#!/usr/bin/env python3
"""
EVE Universe Database Generator

Extracts EVE Universe data from Phobos output and creates a normalized SQLite database
with systems, constellations, regions, and jump connections.

Usage:
    python generate.py --output eve_universe.db --phobos-output ./output
"""

import sys
import os
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


from typing import List, Dict, Any


def _parse_float(value):
    """Parse a float value from string, handling special cases."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if value.lower() in ('inf', 'infinity'):
            return None  # Store inf as NULL
        if value.lower() in ('nan', '-nan'):
            return None
        try:
            return float(value)
        except ValueError:
            return None
    return None

def _parse_bool(value):
    """Parse a boolean value from string."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, str):
        return 1 if value.lower() == 'true' else 0
    return None

def extract_fsd_dict_data(fsd_entry: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract data from FSD_DICT structure into flat dictionary."""
    result = {}
    for item in fsd_entry:
        if isinstance(item, dict):
            for key, value in item.items():
                result[key] = value
    return result


def create_database_schema(conn: sqlite3.Connection) -> None:
    """Create the database schema."""
    print("Creating database schema...")
    
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute('DROP TABLE IF EXISTS jumps')
    cursor.execute('DROP TABLE IF EXISTS systems')
    cursor.execute('DROP TABLE IF EXISTS constellations')
    cursor.execute('DROP TABLE IF EXISTS regions')
    cursor.execute('DROP TABLE IF EXISTS SolarSystems')
    cursor.execute('DROP TABLE IF EXISTS Constellations')
    cursor.execute('DROP TABLE IF EXISTS Regions')
    cursor.execute('DROP TABLE IF EXISTS Jumps')
    cursor.execute('DROP TABLE IF EXISTS Planets')
    cursor.execute('DROP TABLE IF EXISTS Moons')
    cursor.execute('DROP TABLE IF EXISTS NpcStations')
    cursor.execute('DROP TABLE IF EXISTS LagrangePoints')
    cursor.execute('DROP TABLE IF EXISTS Types')
    
    # Regions table
    cursor.execute('''
        CREATE TABLE Regions (
            regionId INTEGER PRIMARY KEY,
            name TEXT,
            centerX REAL,
            centerY REAL,
            centerZ REAL
        )
    ''')
    
    # Constellations table
    cursor.execute('''
        CREATE TABLE Constellations (
            constellationId INTEGER PRIMARY KEY,
            name TEXT,
            regionId INTEGER,
            centerX REAL,
            centerY REAL,
            centerZ REAL,
            FOREIGN KEY (regionId) REFERENCES Regions (regionId)
        )
    ''')
    
    # Systems table (named SolarSystems to match reference)
    cursor.execute('''
        CREATE TABLE SolarSystems (
            solarSystemId INTEGER PRIMARY KEY,
            name TEXT,
            constellationId INTEGER,
            regionId INTEGER,
            centerX REAL,
            centerY REAL,
            centerZ REAL,
            frost_line REAL,
            habitable_zone_inner REAL,
            habitable_zone_outer REAL,
            star_age REAL,
            star_luminosity REAL,
            star_mass REAL,
            star_metallicity REAL,
            star_radius REAL,
            star_spectral_class TEXT,
            star_temperature REAL,
            FOREIGN KEY (constellationId) REFERENCES Constellations (constellationId),
            FOREIGN KEY (regionId) REFERENCES Regions (regionId)
        )
    ''')    # Jumps table
    cursor.execute('''
        CREATE TABLE Jumps (
            fromSystemId INTEGER,
            toSystemId INTEGER,
            fromCenterX REAL,
            fromCenterY REAL,
            fromCenterZ REAL,
            toCenterX REAL,
            toCenterY REAL,
            toCenterZ REAL,
            jumpType INTEGER,
            PRIMARY KEY (fromSystemId, toSystemId),
            FOREIGN KEY (fromSystemId) REFERENCES SolarSystems (solarSystemId),
            FOREIGN KEY (toSystemId) REFERENCES SolarSystems (solarSystemId)
        )
    ''')
    
    # Planets table
    cursor.execute('''
        CREATE TABLE Planets (
            planetId INTEGER PRIMARY KEY,
            name TEXT,
            solarSystemId INTEGER,
            celestialIndex INTEGER,
            typeId INTEGER,
            centerX REAL,
            centerY REAL,
            centerZ REAL,
            radius REAL,
            density REAL,
            eccentricity REAL,
            escapeVelocity REAL,
            surfaceGravity REAL,
            temperature REAL,
            pressure REAL,
            orbitRadius REAL,
            orbitPeriod REAL,
            rotationRate REAL,
            mass REAL,
            typeDescription TEXT,
            FOREIGN KEY (solarSystemId) REFERENCES SolarSystems (solarSystemId)
        )
    ''')
    
    # Moons table
    cursor.execute('''
        CREATE TABLE Moons (
            moonId INTEGER PRIMARY KEY,
            name TEXT,
            planetId INTEGER,
            solarSystemId INTEGER,
            typeId INTEGER,
            centerX REAL,
            centerY REAL,
            centerZ REAL,
            radius REAL,
            density REAL,
            eccentricity REAL,
            escapeVelocity REAL,
            surfaceGravity REAL,
            temperature REAL,
            pressure REAL,
            orbitRadius REAL,
            orbitPeriod REAL,
            rotationRate REAL,
            mass REAL,
            spectralClass TEXT,
            typeDescription TEXT,
            FOREIGN KEY (planetId) REFERENCES Planets (planetId),
            FOREIGN KEY (solarSystemId) REFERENCES SolarSystems (solarSystemId)
        )
    ''')
    
    # NPC Stations table
    cursor.execute('''
        CREATE TABLE NpcStations (
            stationId INTEGER PRIMARY KEY,
            name TEXT,
            solarSystemId INTEGER,
            planetId INTEGER,
            typeId INTEGER,
            ownerId INTEGER,
            centerX REAL,
            centerY REAL,
            centerZ REAL,
            lagrangePoint INTEGER,
            orbitId INTEGER,
            operationId INTEGER,
            isConquerable BOOLEAN,
            reprocessingEfficiency REAL,
            reprocessingStationsTake REAL,
            FOREIGN KEY (solarSystemId) REFERENCES SolarSystems (solarSystemId),
            FOREIGN KEY (planetId) REFERENCES Planets (planetId)
        )
    ''')
    
    # Lagrange Points table
    cursor.execute('''
        CREATE TABLE LagrangePoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solarSystemId INTEGER,
            planetId INTEGER,
            pointType TEXT,
            centerX REAL,
            centerY REAL,
            centerZ REAL,
            FOREIGN KEY (solarSystemId) REFERENCES SolarSystems (solarSystemId),
            FOREIGN KEY (planetId) REFERENCES Planets (planetId)
        )
    ''')
    
    # Types table for type ID to name lookups
    cursor.execute('''
        CREATE TABLE Types (
            typeId INTEGER PRIMARY KEY,
            typeName TEXT NOT NULL,
            groupId INTEGER,
            description TEXT,
            published INTEGER,
            mass REAL,
            volume REAL,
            capacity REAL,
            portionSize INTEGER,
            basePrice REAL,
            marketGroupId INTEGER,
            iconId INTEGER,
            soundId INTEGER,
            graphicId INTEGER
        )
    ''')
    
    # Create indexes for common type lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_types_name ON Types(typeName)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_types_groupId ON Types(groupId)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_types_marketGroupId ON Types(marketGroupId)')
    
    conn.commit()
    print("Database schema created")


def load_types_data(conn: sqlite3.Connection, phobos_path: Path) -> int:
    """Load types data from fsd_built/types.json into the database."""
    print("Loading types data...")
    
    types_file = phobos_path / 'fsd_built' / 'types.json'
    if not types_file.exists():
        print("Warning: types.json not found, skipping types data")
        return 0
    
    cursor = conn.cursor()
    
    with open(types_file, 'r', encoding='utf-8') as f:
        types_data = json.load(f)
    
    print(f"Found {len(types_data)} types")
    
    count = 0
    skipped = 0
    filtered = 0
    
    # Legacy/unused group IDs to exclude
    excluded_groups = {920, 186, 226, 306, 526, 952, 1568, 1667, 1724, 1876, 1975, 4079, 4609, 4770, 4780, 4814, 5004}
    
    for type_id_str, type_data in types_data.items():
        type_id = int(type_id_str)
        
        # Extract name - handle localization fields
        name = None
        for key in ['typeName_en-us', 'typeName', 'name_en-us', 'name']:
            if key in type_data:
                name = type_data[key]
                break
        
        # Skip types without names
        if not name:
            skipped += 1
            continue
        
        # Extract fields for filtering
        published = type_data.get('published', 0)
        mass = _parse_float(type_data.get('mass'))
        group_id = type_data.get('groupID')
        
        # Apply filters: published=1, mass>0, groupId not in excluded list
        if published != 1:
            filtered += 1
            continue
        if mass is None or mass <= 0:
            filtered += 1
            continue
        if group_id in excluded_groups:
            filtered += 1
            continue
        
        # Extract description
        description = None
        for key in ['description_en-us', 'description']:
            if key in type_data:
                description = type_data[key]
                break
        
        cursor.execute('''
            INSERT INTO Types (
                typeId, typeName, groupId, description, published,
                mass, volume, capacity, portionSize, basePrice,
                marketGroupId, iconId, soundId, graphicId
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            type_id,
            name,
            group_id,
            description,
            published,
            mass,
            _parse_float(type_data.get('volume')),
            _parse_float(type_data.get('capacity')),
            type_data.get('portionSize'),
            _parse_float(type_data.get('basePrice')),
            type_data.get('marketGroupID'),
            type_data.get('iconID'),
            type_data.get('soundID'),
            type_data.get('graphicID')
        ))
        
        count += 1
        if count % 5000 == 0:
            print(f"  Inserted {count} types...")
    
    conn.commit()
    print(f"Loaded {count} types")
    if skipped > 0:
        print(f"Skipped {skipped} types without names")
    if filtered > 0:
        print(f"Filtered {filtered} types (unpublished, no mass, or excluded groups)")
    
    return count


def process_eve_data(phobos_output_dir: str, db_path: str) -> None:
    """Main processing function."""
    phobos_path = Path(phobos_output_dir)
    
    print("Starting EVE Universe data processing...")
    print(f"Phobos output directory: {phobos_path}")
    print(f"Output database: {db_path}")
    
    # Load localization data for names
    print("Loading localization data...")
    localization_names = {}
    loc_path = phobos_path / 'resource_pickle' / 'res__localizationfsd_localization_fsd_en-us.json'
    if loc_path.exists():
        with open(loc_path, 'r', encoding='utf-8') as f:
            loc_data = json.load(f)
            
        if isinstance(loc_data, list) and len(loc_data) > 1 and isinstance(loc_data[1], dict):
            for id_str, name_data in loc_data[1].items():
                if isinstance(name_data, list) and len(name_data) > 0 and name_data[0]:
                    try:
                        localization_names[int(id_str)] = name_data[0]
                    except ValueError:
                        continue  # Skip non-numeric IDs
        
        print(f"Loaded {len(localization_names)} localized names")
    else:
        print("Warning: Localization file not found, using generic names")
    
    # Create database
    conn = sqlite3.connect(db_path)
    create_database_schema(conn)
    cursor = conn.cursor()
    
    # Helper functions for data parsing
    def _parse_float(value):
        """Safely parse float value from FSD data"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_bool(value):
        """Safely parse boolean value from FSD data"""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return None
    
    # Initialize counters
    region_count = 0
    constellation_count = 0
    system_count = 0
    jump_count = 0
    planet_count = 0
    moon_count = 0
    station_count = 0
    
    # Load regions
    print("Loading regions...")
    regions_path = phobos_path / 'fsd_binary_schema' / 'regions.json'
    if not regions_path.exists():
        raise FileNotFoundError(f"Regions file not found: {regions_path}")
    
    with open(regions_path, 'r', encoding='utf-8') as f:
        regions_data = json.load(f)
    
    for region_id_str, region_data in regions_data.items():
        region_id = int(region_id_str)
        name_id = region_data.get('nameID')
        
        # Extract 3D coordinates from center array
        center_data = region_data.get('center', [])
        x, y, z = None, None, None
        # center is [schema_dict, x_str, y_str, z_str]
        if len(center_data) >= 4:
            try:
                x = float(center_data[1])
                y = float(center_data[2])
                z = float(center_data[3])
            except (ValueError, TypeError):
                pass
        
        # Convert nameID to int if it's a string
        if isinstance(name_id, str):
            try:
                name_id = int(name_id)
            except ValueError:
                name_id = None
        
        # Use nameID for localization lookup, fallback to region_id, then generic name
        if name_id and name_id in localization_names:
            region_name = localization_names[name_id]
        elif region_id in localization_names:
            region_name = localization_names[region_id]
        else:
            region_name = f'Region {region_id}'
            
        cursor.execute('''
            INSERT INTO Regions (regionId, name, centerX, centerY, centerZ) 
            VALUES (?, ?, ?, ?, ?)
        ''', (region_id, region_name, x, y, z))
        region_count += 1
    
    conn.commit()
    print(f"Inserted {region_count} regions")
    
    # Load constellations
    print("Loading constellations...")
    constellations_path = phobos_path / 'fsd_binary_schema' / 'constellations.json'
    if not constellations_path.exists():
        raise FileNotFoundError(f"Constellations file not found: {constellations_path}")
    
    with open(constellations_path, 'r', encoding='utf-8') as f:
        constellations_data = json.load(f)
    
    constellation_count = 0
    for constellation_id_str, constellation_data in constellations_data.items():
        constellation_id = int(constellation_id_str)
        region_id = constellation_data.get('regionID')
        name_id = constellation_data.get('nameID')
        
        # Extract 3D coordinates from center array
        center_data = constellation_data.get('center', [])
        x, y, z = None, None, None
        # center is [schema_dict, x_str, y_str, z_str]
        if len(center_data) >= 4:
            try:
                x = float(center_data[1])
                y = float(center_data[2])
                z = float(center_data[3])
            except (ValueError, TypeError):
                pass
        
        # Convert IDs to int if they're strings
        if isinstance(region_id, str):
            try:
                region_id = int(region_id)
            except ValueError:
                region_id = None
        
        if isinstance(name_id, str):
            try:
                name_id = int(name_id)
            except ValueError:
                name_id = None
        
        # Use nameID for localization lookup, fallback to constellation_id, then generic name
        if name_id and name_id in localization_names:
            constellation_name = localization_names[name_id]
        elif constellation_id in localization_names:
            constellation_name = localization_names[constellation_id]
        else:
            constellation_name = f'Constellation {constellation_id}'
        
        cursor.execute('''
            INSERT INTO Constellations (constellationId, name, regionId, centerX, centerY, centerZ) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (constellation_id, constellation_name, region_id, x, y, z))
        constellation_count += 1
    
    conn.commit()
    print(f"Inserted {constellation_count} constellations")
    
    # Load systems
    print("Loading systems...")
    systems_path = phobos_path / 'fsd_binary_schema' / 'systems.json'
    
    # Also load solarsystemcontent.json for star statistics
    systems_content_path = phobos_path / 'fsd_binary_schema' / 'solarsystemcontent.json'
    star_statistics = {}
    
    if systems_content_path.exists():
        print("Loading star statistics from solarsystemcontent.json...")
        with open(systems_content_path, 'r', encoding='utf-8') as f:
            systems_content_data = json.load(f)
        
        if 'Type: FSD Multi Index' in systems_content_data:
            content_data = systems_content_data['Type: FSD Multi Index']
        else:
            content_data = systems_content_data
        
        # Extract star statistics for each system
        for system_dict in content_data:
            for system_id_str, system_entries in system_dict.items():
                if isinstance(system_entries, list):
                    try:
                        system_id = int(system_id_str)
                        system_data = extract_fsd_dict_data(system_entries)
                        star_key = f'{system_id}.star'
                        
                        if star_key in system_data and isinstance(system_data[star_key], list):
                            star_data = extract_fsd_dict_data(system_data[star_key])
                            stats_data = star_data.get('star.statistics', [])
                            
                            # Parse statistics list
                            stats = {}
                            if isinstance(stats_data, list):
                                for stat_item in stats_data:
                                    if isinstance(stat_item, dict):
                                        for stat_key, stat_value in stat_item.items():
                                            field_name = stat_key.replace('statistics.', '')
                                            stats[field_name] = stat_value
                            
                            star_statistics[system_id] = stats
                    except ValueError:
                        continue
        
        print(f"Loaded star statistics for {len(star_statistics)} systems")
    
    # Load systems from systems.json
    if systems_path.exists():
        with open(systems_path, 'r', encoding='utf-8') as f:
            systems_file_data = json.load(f)
        
        system_count = 0
        
        # Handle simple dict structure (new format)
        for system_id_str, system_data in systems_file_data.items():
            try:
                system_id = int(system_id_str)
                
                constellation_id = system_data.get('constellationID')
                region_id = system_data.get('regionID') 
                name_id = system_data.get('nameID')
                
                # Extract additional system data
                frost_line = system_data.get('frostLine')
                habitable_zone_raw = system_data.get('habitableZone')
                
                # Parse habitable zone data (could be string or list)
                habitable_zone_inner, habitable_zone_outer = None, None
                if isinstance(habitable_zone_raw, str):
                    try:
                        # Try to parse as Python literal (list)
                        import ast
                        habitable_zone = ast.literal_eval(habitable_zone_raw)
                        if isinstance(habitable_zone, list) and len(habitable_zone) >= 2:
                            habitable_zone_inner, habitable_zone_outer = float(habitable_zone[0]), float(habitable_zone[1])
                    except (ValueError, SyntaxError):
                        pass
                elif isinstance(habitable_zone_raw, list) and len(habitable_zone_raw) >= 2:
                    habitable_zone_inner, habitable_zone_outer = float(habitable_zone_raw[0]), float(habitable_zone_raw[1])
                
                # Extract 3D coordinates from center array
                center_data = system_data.get('center', [])
                x, y, z = None, None, None
                # center is [schema_dict, x_str, y_str, z_str]
                if len(center_data) >= 4:
                    try:
                        x = float(center_data[1])
                        y = float(center_data[2])
                        z = float(center_data[3])
                    except (ValueError, TypeError):
                        pass
                
                # Convert IDs to int if they're strings
                if isinstance(constellation_id, str):
                    try:
                        constellation_id = int(constellation_id)
                    except ValueError:
                        constellation_id = None
                        
                if isinstance(region_id, str):
                    try:
                        region_id = int(region_id)
                    except ValueError:
                        region_id = None
                
                if isinstance(name_id, str):
                    try:
                        name_id = int(name_id)
                    except ValueError:
                        name_id = None
                
                # Use nameID for localization lookup, fallback to system_id, then generic name
                if name_id and name_id in localization_names:
                    system_name = localization_names[name_id]
                elif system_id in localization_names:
                    system_name = localization_names[system_id]
                else:
                    system_name = f'System {system_id}'
                
                # Get star statistics
                star_stats = star_statistics.get(system_id, {})
                star_age = _parse_float(star_stats.get('age'))
                star_luminosity = _parse_float(star_stats.get('luminosity'))
                star_mass = _parse_float(star_stats.get('mass'))
                star_metallicity = _parse_float(star_stats.get('metallicity'))
                star_radius = _parse_float(star_stats.get('radius'))
                star_spectral_class = star_stats.get('spectralClass')
                star_temperature = _parse_float(star_stats.get('temperature'))
                
                cursor.execute('''
                    INSERT OR IGNORE INTO SolarSystems (solarSystemId, name, constellationId, regionId, centerX, centerY, centerZ,
                                             frost_line, habitable_zone_inner, habitable_zone_outer, star_age, star_luminosity, star_mass, 
                                             star_metallicity, star_radius, star_spectral_class, star_temperature) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (system_id, system_name, constellation_id, region_id, x, y, z,
                      frost_line, habitable_zone_inner, habitable_zone_outer, star_age, star_luminosity, star_mass, star_metallicity, star_radius, star_spectral_class, star_temperature))
                system_count += 1
            except (ValueError, KeyError) as e:
                continue
        
        conn.commit()
        print(f"Inserted {system_count} systems from systems.json")
    
    # Fallback to solarsystemcontent.json if systems.json doesn't work
    if system_count == 0:
        print("No systems found in systems.json, trying solarsystemcontent.json...")
        systems_path = phobos_path / 'fsd_binary_schema' / 'solarsystemcontent.json'
        if not systems_path.exists():
            raise FileNotFoundError(f"Systems file not found: {systems_path}")
        
        with open(systems_path, 'r', encoding='utf-8') as f:
            systems_file_data = json.load(f)
        
        if 'Type: FSD Multi Index' in systems_file_data:
            systems_data = systems_file_data['Type: FSD Multi Index']
        else:
            systems_data = systems_file_data
        
        processed_systems = set()
        system_count = 0
        
        for system_dict in systems_data:
            for system_id_str, system_entries in system_dict.items():
                try:
                    system_id = int(system_id_str)
                    if system_id in processed_systems:
                        continue
                    processed_systems.add(system_id)
                    
                    # Handle both list and string entries
                    if isinstance(system_entries, list):
                        system_data = extract_fsd_dict_data(system_entries)
                        constellation_id = system_data.get(f'{system_id}.constellationID')
                        region_id = system_data.get(f'{system_id}.regionID')
                        name_id = system_data.get(f'{system_id}.nameID')
                        
                        # Extract additional system data
                        frost_line = system_data.get(f'{system_id}.frostLine')
                        habitable_zone_raw = system_data.get(f'{system_id}.habitableZone')
                        
                        # Parse habitable zone data (could be string or list)
                        habitable_zone_inner, habitable_zone_outer = None, None
                        if isinstance(habitable_zone_raw, str):
                            try:
                                # Try to parse as Python literal (list)
                                import ast
                                habitable_zone = ast.literal_eval(habitable_zone_raw)
                                if isinstance(habitable_zone, list) and len(habitable_zone) >= 2:
                                    habitable_zone_inner, habitable_zone_outer = float(habitable_zone[0]), float(habitable_zone[1])
                            except (ValueError, SyntaxError):
                                pass
                        elif isinstance(habitable_zone_raw, list) and len(habitable_zone_raw) >= 2:
                            habitable_zone_inner, habitable_zone_outer = float(habitable_zone_raw[0]), float(habitable_zone_raw[1])
                        
                        # Extract 3D coordinates from center.vector_data
                        center_data = system_data.get(f'{system_id}.center', [])
                        x, y, z = None, None, None
                        if len(center_data) >= 2 and isinstance(center_data[1], dict):
                            vector_data = center_data[1].get('vector_data', [])
                            if len(vector_data) >= 3:
                                x, y, z = vector_data[0], vector_data[1], vector_data[2]
                        
                        # Convert nameID to int if it's a string
                        if isinstance(name_id, str):
                            try:
                                name_id = int(name_id)
                            except ValueError:
                                name_id = None
                        
                        # Use nameID for localization lookup, fallback to system_id, then generic name
                        if name_id and name_id in localization_names:
                            system_name = localization_names[name_id]
                        elif system_id in localization_names:
                            system_name = localization_names[system_id]
                        else:
                            system_name = f'System {system_id}'
                        
                        # Get star statistics
                        star_stats = star_statistics.get(system_id, {})
                        star_age = _parse_float(star_stats.get('age'))
                        star_luminosity = _parse_float(star_stats.get('luminosity'))
                        star_mass = _parse_float(star_stats.get('mass'))
                        star_metallicity = _parse_float(star_stats.get('metallicity'))
                        star_radius = _parse_float(star_stats.get('radius'))
                        star_spectral_class = star_stats.get('spectralClass')
                        star_temperature = _parse_float(star_stats.get('temperature'))
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO SolarSystems (solarSystemId, name, constellationId, regionId, centerX, centerY, centerZ, frost_line, habitable_zone_inner, habitable_zone_outer,
                                               star_age, star_luminosity, star_mass, star_metallicity, star_radius, star_spectral_class, star_temperature) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (system_id, system_name, constellation_id, region_id, x, y, z, frost_line, habitable_zone_inner, habitable_zone_outer,
                              star_age, star_luminosity, star_mass, star_metallicity, star_radius, star_spectral_class, star_temperature))
                        system_count += 1
                    elif isinstance(system_entries, str):
                        # String entries might just be system IDs, we still need the data
                        # For now, insert with minimal info and get constellation/region from jumps data
                        system_name = localization_names.get(system_id, f'System {system_id}')
                        
                        # Get star statistics
                        star_stats = star_statistics.get(system_id, {})
                        star_age = _parse_float(star_stats.get('age'))
                        star_luminosity = _parse_float(star_stats.get('luminosity'))
                        star_mass = _parse_float(star_stats.get('mass'))
                        star_metallicity = _parse_float(star_stats.get('metallicity'))
                        star_radius = _parse_float(star_stats.get('radius'))
                        star_spectral_class = star_stats.get('spectralClass')
                        star_temperature = _parse_float(star_stats.get('temperature'))
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO SolarSystems (solarSystemId, name, constellationId, regionId, centerX, centerY, centerZ, frost_line, habitable_zone_inner, habitable_zone_outer,
                                               star_age, star_luminosity, star_mass, star_metallicity, star_radius, star_spectral_class, star_temperature) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (system_id, system_name, None, None, None, None, None, None,
                              star_age, star_luminosity, star_mass, star_metallicity, star_radius, star_spectral_class, star_temperature))
                        system_count += 1
                except ValueError:
                    continue
        
        conn.commit()
        print(f"Inserted {system_count} systems from solarsystemcontent.json")
    
    # Extract celestial objects (planets, moons, NPC stations)
    print("Extracting celestial objects (planets, moons, stations)...")
    
    planet_count = 0
    moon_count = 0
    station_count = 0
    
    # Load celestials from SQLite miner output (contains planets and moons)
    celestials_path = phobos_path / 'sqlite' / 'app__bin64_staticdata_mapObjects_celestials.json'
    if celestials_path.exists():
        with open(celestials_path, 'r', encoding='utf-8') as f:
            celestials_data = json.load(f)
        
        # Group IDs: 6=Sun, 7=Planet, 8=Moon, 10=Stargate
        for celestial in celestials_data:
            celestial_id = celestial.get('celestialID')
            group_id = celestial.get('groupID')
            system_id = celestial.get('solarSystemID')
            type_id = celestial.get('typeID')
            
            # Extract name (use English)
            name = celestial.get('celestialName_en-us', f'Celestial {celestial_id}')
            
            # Get position
            x = _parse_float(celestial.get('x'))
            y = _parse_float(celestial.get('y'))
            z = _parse_float(celestial.get('z'))
            
            # Get other properties
            radius = _parse_float(celestial.get('radius'))
            celestial_index = celestial.get('celestialIndex')
            orbit_id = celestial.get('orbitID')
            
            if group_id == 7:  # Planet
                cursor.execute('''
                    INSERT OR IGNORE INTO Planets (
                        planetId, name, solarSystemId, celestialIndex, typeId,
                        centerX, centerY, centerZ, radius
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (celestial_id, name, system_id, celestial_index, type_id,
                      x, y, z, radius))
                planet_count += 1
                
            elif group_id == 8:  # Moon
                # For moons, orbitID usually points to the planet
                cursor.execute('''
                    INSERT OR IGNORE INTO Moons (
                        moonId, name, planetId, solarSystemId, typeId,
                        centerX, centerY, centerZ, radius
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (celestial_id, name, orbit_id, system_id, type_id,
                      x, y, z, radius))
                moon_count += 1
    else:
        print(f"Warning: Celestials file not found at {celestials_path}")
    
    # Load NPC stations from SQLite miner output
    stations_path = phobos_path / 'sqlite' / 'app__bin64_staticdata_mapObjects_npcStations.json'
    if stations_path.exists():
        with open(stations_path, 'r', encoding='utf-8') as f:
            stations_data = json.load(f)
        
        for station in stations_data:
            station_id = station.get('stationID')
            system_id = station.get('solarSystemID')
            type_id = station.get('typeID')
            owner_id = station.get('ownerID')
            orbit_id = station.get('orbitID')  # Planet ID if orbiting
            operation_id = station.get('operationID')
            
            # Get position
            x = _parse_float(station.get('x'))
            y = _parse_float(station.get('y'))
            z = _parse_float(station.get('z'))
            
            # Get station-specific properties
            is_conquerable = _parse_bool(station.get('isConquerable'))
            reprocessing_efficiency = _parse_float(station.get('reprocessingEfficiency'))
            reprocessing_take = _parse_float(station.get('reprocessingStationsTake'))
            
            # Station names come from localization
            name = localization_names.get(station_id, f'Station {station_id}')
            
            cursor.execute('''
                INSERT OR IGNORE INTO NpcStations (
                    stationId, name, solarSystemId, planetId, typeId, ownerId,
                    centerX, centerY, centerZ, operationId,
                    isConquerable, reprocessingEfficiency, reprocessingStationsTake
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (station_id, name, system_id, orbit_id, type_id, owner_id,
                  x, y, z, operation_id, is_conquerable,
                  reprocessing_efficiency, reprocessing_take))
            station_count += 1
    else:
        print(f"Warning: NPC stations file not found at {stations_path}")
    
    conn.commit()
    print(f"Inserted {planet_count} planets, {moon_count} moons, and {station_count} NPC stations")
    
    # Extract Lagrange Points
    print("Extracting Lagrange Points...")
    lpoint_count = 0
    
    # Load solarsystemcontent.json which contains Lagrange point data
    systems_content_path = phobos_path / 'fsd_binary_schema' / 'solarsystemcontent.json'
    if systems_content_path.exists():
        with open(systems_content_path, 'r', encoding='utf-8') as f:
            systems_content_data = json.load(f)
        
        if 'Type: FSD Multi Index' in systems_content_data:
            systems_data_for_lpoints = systems_content_data['Type: FSD Multi Index']
        else:
            systems_data_for_lpoints = systems_content_data
        
        for system_dict in systems_data_for_lpoints:
            for system_id_str, system_data in system_dict.items():
                try:
                    system_id = int(system_id_str)
                except ValueError:
                    continue
                
                # Only process dict entries (skip string entries)
                if not isinstance(system_data, dict):
                    continue
                
                # Get planets data
                planets_data = system_data.get('planets', {})
                if isinstance(planets_data, dict):
                    for planet_id_str, planet_data in planets_data.items():
                        try:
                            planet_id = int(planet_id_str)
                        except ValueError:
                            continue
                        
                        # Get lagrange points for this planet
                        lagrange_points = planet_data.get('lagrangePoints', {})
                        if isinstance(lagrange_points, dict):
                            for point_type, point_coords in lagrange_points.items():
                                # point_coords is [schema_dict, x_str, y_str, z_str]
                                if isinstance(point_coords, list) and len(point_coords) >= 4:
                                    try:
                                        x = float(point_coords[1])
                                        y = float(point_coords[2])
                                        z = float(point_coords[3])
                                        
                                        cursor.execute('''
                                            INSERT INTO LagrangePoints (solarSystemId, planetId, pointType, centerX, centerY, centerZ)
                                            VALUES (?, ?, ?, ?, ?, ?)
                                        ''', (system_id, planet_id, point_type, x, y, z))
                                        lpoint_count += 1
                                    except (ValueError, TypeError):
                                        pass
    else:
        print(f"Warning: solarsystemcontent.json not found at {systems_content_path}")
    
    conn.commit()
    print(f"Inserted {lpoint_count} Lagrange Points")
    
    # Extract jumps
    print("Extracting jumps from stargate data...")
    
    # Load celestials data to get stargates (groupID = 10)
    celestials_path = phobos_path / 'sqlite' / 'app__bin64_staticdata_mapObjects_celestials.json'
    if not celestials_path.exists():
        print(f"Warning: Celestials file not found at {celestials_path}, skipping jump extraction")
    else:
        with open(celestials_path, 'r', encoding='utf-8') as f:
            celestials_data = json.load(f)
        
        # Build jump connections from stargates
        # celestialNameID on a stargate is the destination system ID
        jumps = []
        stargate_count = 0
        
        for celestial in celestials_data:
            if celestial.get('groupID') == 10:  # Stargate
                stargate_count += 1
                system_id = celestial.get('solarSystemID')
                dest_system_id = celestial.get('celestialNameID')
                
                # celestialNameID should point to the destination system
                if system_id and dest_system_id and system_id != dest_system_id:
                    jumps.append((system_id, dest_system_id))
        
        print(f"Found {stargate_count} stargates")
        
        # Remove duplicates and insert
        jumps = list(set(jumps))
        print(f"Found {len(jumps)} jump connections")
        
        for from_sys, to_sys in jumps:
            cursor.execute('''
                INSERT OR IGNORE INTO Jumps (
                    fromSystemId, toSystemId, fromCenterX, fromCenterY, fromCenterZ,
                    toCenterX, toCenterY, toCenterZ, jumpType
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (from_sys, to_sys, None, None, None, None, None, None, None))
    
    conn.commit()
    
    # Load types data
    load_types_data(conn, phobos_path)
    
    # Vacuum database
    conn.execute('VACUUM')
    conn.commit()
    
    # Show final statistics
    cursor.execute('SELECT COUNT(*) FROM Regions')
    regions_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM Constellations')  
    constellations_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM SolarSystems')
    systems_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM Jumps')  
    jumps_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM Planets')  
    planets_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM Moons')  
    moons_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM NpcStations')  
    stations_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM LagrangePoints')  
    lpoints_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM Types')  
    types_count = cursor.fetchone()[0]
    
    print(f"Successfully created database: {db_path}")
    print("Database contains:")
    print(f"  - {regions_count:,} regions")
    print(f"  - {constellations_count:,} constellations")
    print(f"  - {systems_count:,} systems")
    print(f"  - {jumps_count:,} jump connections")
    print(f"  - {planets_count:,} planets")
    print(f"  - {moons_count:,} moons")
    print(f"  - {stations_count:,} NPC stations")
    print(f"  - {lpoints_count:,} Lagrange Points")
    print(f"  - {types_count:,} types")
    
    conn.close()


def run_simple_query(db_path: str, query: str):
    """Run a simple query and display results."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            if results:
                print(f"\nQuery results ({len(results)} rows):")
                for i, row in enumerate(results[:20]):  # Limit to first 20 results
                    print(f"  {i+1}: {row}")
                if len(results) > 20:
                    print(f"  ... ({len(results) - 20} more rows)")
            else:
                print("\nQuery returned no results.")
                
    except Exception as e:
        print(f"Query error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Process Phobos EVE data into SQLite database')
    parser.add_argument('--output', '-o', 
                       default='eve_universe.db',
                       help='Output SQLite database path (default: eve_universe.db)')
    parser.add_argument('--phobos-output', '-p',
                       default='./output',
                       help='Path to Phobos output directory (default: ./output)')
    parser.add_argument('--query', '-q',
                       help='Run a simple query on the database after creation')
    
    args = parser.parse_args()
    
    # Verify Python version
    if sys.version_info < (3, 7):
        print("Error: This script requires Python 3.7 or higher")
        sys.exit(1)
    
    # Verify phobos output directory exists
    if not os.path.exists(args.phobos_output):
        print(f"Error: Phobos output directory does not exist: {args.phobos_output}")
        sys.exit(1)
    
    try:
        process_eve_data(args.phobos_output, args.output)
        
        # Run query if specified
        if args.query:
            run_simple_query(args.output, args.query)
        
        print("\nProcessing complete!")
        print("\nYou can now query the database with tools like sqlite3 or DB Browser for SQLite.")
        print("Example queries:")
        print("  SELECT name FROM SolarSystems LIMIT 10;")
        print("  SELECT typeName FROM Types WHERE typeId = 34;")
        print("  SELECT typeId, typeName FROM Types WHERE typeName LIKE '%Tritanium%';")
        print("  SELECT r.name as region, COUNT(s.solarSystemId) as system_count")
        print("    FROM Regions r JOIN SolarSystems s ON r.regionId = s.regionId GROUP BY r.name;")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()