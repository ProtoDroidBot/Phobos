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
    
    conn.commit()
    print("Database schema created")


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
    
    # Create a lookup for system names (needed for proper planet/moon naming)
    system_names = {}
    cursor.execute("SELECT solarSystemId, name FROM SolarSystems")
    for sys_id, sys_name in cursor.fetchall():
        system_names[sys_id] = sys_name
    
    # Load solarsystemcontent.json for celestial objects data
    systems_content_path = phobos_path / 'fsd_binary_schema' / 'solarsystemcontent.json'
    if not systems_content_path.exists():
        print("Warning: solarsystemcontent.json not found, skipping celestial objects extraction")
    else:
        with open(systems_content_path, 'r', encoding='utf-8') as f:
            systems_content_data = json.load(f)
        
        if 'Type: FSD Multi Index' in systems_content_data:
            systems_data_for_celestials = systems_content_data['Type: FSD Multi Index']
        else:
            systems_data_for_celestials = systems_content_data
        
        # TODO: Fix planet/moon/station extraction for new JSON format
        # The structure has changed and needs to be updated
        pass
    
    conn.commit()
    print(f"Inserted {planet_count} planets, {moon_count} moons, and {station_count} NPC stations")
    
    # Extract Lagrange Points
    print("Extracting Lagrange Points...")
    lpoint_count = 0
    
    # Reuse the already loaded systems_content_data (it's a list of dicts)
    for system_dict in systems_data_for_celestials:
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
    
    conn.commit()
    print(f"Inserted {lpoint_count} Lagrange Points")
    
    # Extract jumps
    print("Extracting jumps from stargate data...")
    
    # Load solarsystemcontent.json for jump data
    systems_content_path = phobos_path / 'fsd_binary_schema' / 'solarsystemcontent.json'
    if not systems_content_path.exists():
        print("Warning: solarsystemcontent.json not found, skipping jump extraction")
        return
        
    with open(systems_content_path, 'r', encoding='utf-8') as f:
        systems_content_data = json.load(f)
    
    if 'Type: FSD Multi Index' in systems_content_data:
        systems_data_for_jumps = systems_content_data['Type: FSD Multi Index']
    else:
        systems_data_for_jumps = systems_content_data
    
    # First pass: Build stargate-to-system mapping
    stargate_to_system = {}
    for system_dict in systems_data_for_jumps:
        for system_id_str, system_entries in system_dict.items():
            try:
                system_id = int(system_id_str)
            except ValueError:
                continue
            
            if isinstance(system_entries, list):
                system_data = extract_fsd_dict_data(system_entries)
                stargates_data = system_data.get(f'{system_id}.stargates', [])
                
                for stargate_info in stargates_data:
                    if isinstance(stargate_info, dict):
                        for stargate_key in stargate_info.keys():
                            if stargate_key.startswith('stargates.'):
                                stargate_id = int(stargate_key.split('.')[-1])
                                stargate_to_system[stargate_id] = system_id
    
    print(f"Found {len(stargate_to_system)} stargates")
    
    # Second pass: Extract jump connections
    jumps = []
    for system_dict in systems_data_for_jumps:
        for system_id_str, system_entries in system_dict.items():
            try:
                system_id = int(system_id_str)
            except ValueError:
                continue
            
            if isinstance(system_entries, list):
                system_data = extract_fsd_dict_data(system_entries)
                stargates_data = system_data.get(f'{system_id}.stargates', [])
                
                for stargate_info in stargates_data:
                    if isinstance(stargate_info, dict):
                        for stargate_key, stargate_details in stargate_info.items():
                            if isinstance(stargate_details, list):
                                for detail_dict in stargate_details:
                                    if isinstance(detail_dict, dict):
                                        for detail_key, detail_value in detail_dict.items():
                                            if '.destination' in detail_key:
                                                try:
                                                    dest_stargate_id = int(detail_value)
                                                    dest_system_id = stargate_to_system.get(dest_stargate_id)
                                                    if dest_system_id and dest_system_id != system_id:
                                                        jumps.append((system_id, dest_system_id))
                                                except ValueError:
                                                    pass
    
    # Remove duplicates and insert
    jumps = list(set(jumps))
    print(f"Found {len(jumps)} jump connections")
    
    for from_sys, to_sys in jumps:
        cursor.execute('INSERT OR IGNORE INTO Jumps (fromSystemId, toSystemId, fromCenterX, fromCenterY, fromCenterZ, toCenterX, toCenterY, toCenterZ, jumpType) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                      (from_sys, to_sys, None, None, None, None, None, None, None))
    
    conn.commit()
    
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
        print("  SELECT r.name as region, COUNT(s.solarSystemId) as system_count")
        print("    FROM Regions r JOIN SolarSystems s ON r.regionId = s.regionId GROUP BY r.name;")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()