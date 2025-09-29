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
    for entry in regions_data:
        for fsd_key, fsd_data in entry.items():
            if fsd_key.startswith('FSD_DICT.'):
                region_id = int(fsd_key.replace('FSD_DICT.', ''))
                region_data = extract_fsd_dict_data(fsd_data)
                name_id = region_data.get(f'{region_id}.nameID')
                
                # Extract 3D coordinates from center.vector_data
                center_data = region_data.get(f'{region_id}.center', [])
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
    for entry in constellations_data:
        for fsd_key, fsd_data in entry.items():
            if fsd_key.startswith('FSD_DICT.'):
                constellation_id = int(fsd_key.replace('FSD_DICT.', ''))
                constellation_data = extract_fsd_dict_data(fsd_data)
                region_id = constellation_data.get(f'{constellation_id}.regionID')
                name_id = constellation_data.get(f'{constellation_id}.nameID')
                
                # Extract 3D coordinates from center.vector_data
                center_data = constellation_data.get(f'{constellation_id}.center', [])
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
    
    # First try systems.json
    if systems_path.exists():
        with open(systems_path, 'r', encoding='utf-8') as f:
            systems_file_data = json.load(f)
        
        processed_systems = set()
        system_count = 0
        
        # Handle if systems.json is a list (like regions/constellations pattern)
        if isinstance(systems_file_data, list):
            for system_dict in systems_file_data:
                for fsd_key, fsd_data in system_dict.items():
                    if fsd_key.startswith('FSD_DICT.') and isinstance(fsd_data, list):
                        try:
                            system_id = int(fsd_key.replace('FSD_DICT.', ''))
                            if system_id in processed_systems:
                                continue
                            processed_systems.add(system_id)
                            
                            system_data = extract_fsd_dict_data(fsd_data)
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
                                INSERT OR IGNORE INTO SolarSystems (solarSystemId, name, constellationId, regionId, centerX, centerY, centerZ,
                                                         frost_line, habitable_zone_inner, habitable_zone_outer, star_age, star_luminosity, star_mass, 
                                                         star_metallicity, star_radius, star_spectral_class, star_temperature) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (system_id, system_name, constellation_id, region_id, x, y, z,
                                  frost_line, habitable_zone_inner, habitable_zone_outer, star_age, star_luminosity, star_mass, star_metallicity, star_radius, star_spectral_class, star_temperature))
                            system_count += 1
                        except ValueError:
                            continue
        else:
            # Handle if systems.json is a dict
            for fsd_key, fsd_data in systems_file_data.items():
                if fsd_key.startswith('FSD_DICT.') and isinstance(fsd_data, list):
                    try:
                        system_id = int(fsd_key.replace('FSD_DICT.', ''))
                        if system_id in processed_systems:
                            continue
                        processed_systems.add(system_id)
                        
                        system_data = extract_fsd_dict_data(fsd_data)
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
                    except ValueError:
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
        
        # Process celestial objects - simplified version for now
        for system_dict in systems_data_for_celestials:
            for system_id_str, system_entries in system_dict.items():
                try:
                    system_id = int(system_id_str)
                except ValueError:
                    continue
                
                if isinstance(system_entries, list):
                    system_data = extract_fsd_dict_data(system_entries)
                    planets_data = system_data.get(f'{system_id}.planets', [])
                    
                    # Extract basic planet information
                    for planet_info in planets_data:
                        if isinstance(planet_info, dict):
                            for planet_key, planet_details in planet_info.items():
                                if planet_key.startswith('planets.'):
                                    try:
                                        planet_id = int(planet_key.split('.')[-1])
                                        
                                        # Get system name for proper planet naming
                                        system_name = system_names.get(system_id, f'System {system_id}')
                                        
                                        # Extract basic planet data (especially celestialIndex for naming)
                                        position = [None, None, None]
                                        radius = None
                                        type_id = None
                                        celestial_index = None
                                        density = None
                                        eccentricity = None
                                        escape_velocity = None
                                        surface_gravity = None
                                        temperature = None
                                        pressure = None
                                        orbit_radius = None
                                        orbit_period = None
                                        rotation_rate = None
                                        mass = None
                                        type_description = None
                                        
                                        # First pass: extract celestialIndex for proper naming
                                        if isinstance(planet_details, list):
                                            for detail in planet_details:
                                                if isinstance(detail, dict):
                                                    for detail_key, detail_value in detail.items():
                                                        if detail_key == f'{planet_id}.celestialIndex':
                                                            celestial_index = _parse_float(detail_value)
                                                            break
                                        
                                        # Generate proper planet name: "SystemName - Planet X"
                                        if celestial_index:
                                            planet_name = f"{system_name} - Planet {int(celestial_index)}"
                                        else:
                                            planet_name = f"{system_name} - Planet {planet_id}"
                                        
                                        if isinstance(planet_details, list):
                                            for detail in planet_details:
                                                if isinstance(detail, dict):
                                                    for detail_key, detail_value in detail.items():
                                                        if detail_key == f'{planet_id}.position':
                                                            if isinstance(detail_value, list) and len(detail_value) >= 2:
                                                                vector_data = detail_value[1].get('vector_data', [])
                                                                if len(vector_data) >= 3:
                                                                    position = vector_data[:3]
                                                        elif detail_key == f'{planet_id}.radius':
                                                            radius = _parse_float(detail_value)
                                                        elif detail_key == f'{planet_id}.typeID':
                                                            type_id = _parse_float(detail_value)
                                                        elif detail_key == f'{planet_id}.celestialIndex':
                                                            celestial_index = _parse_float(detail_value)
                                                        elif detail_key == f'{planet_id}.statistics':
                                                            # Extract detailed statistics from the statistics object
                                                            if isinstance(detail_value, list):
                                                                for stat_entry in detail_value:
                                                                    if isinstance(stat_entry, dict):
                                                                        for stat_key, stat_value in stat_entry.items():
                                                                            if stat_key == 'statistics.density':
                                                                                density = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.eccentricity':
                                                                                eccentricity = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.escapeVelocity':
                                                                                escape_velocity = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.surfaceGravity':
                                                                                surface_gravity = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.temperature':
                                                                                temperature = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.pressure':
                                                                                pressure = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.orbitRadius':
                                                                                orbit_radius = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.orbitPeriod':
                                                                                orbit_period = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.rotationRate':
                                                                                rotation_rate = _parse_float(stat_value)
                                                                            elif stat_key == 'statistics.massDust':
                                                                                # Calculate total mass from dust + gas
                                                                                mass_dust = _parse_float(stat_value)
                                                                                if mass_dust and mass is None:
                                                                                    mass = mass_dust
                                                                            elif stat_key == 'statistics.massGas':
                                                                                mass_gas = _parse_float(stat_value)
                                                                                if mass_gas:
                                                                                    if mass:
                                                                                        mass += mass_gas  # Add gas to dust
                                                                                    else:
                                                                                        mass = mass_gas
                                                                            elif stat_key == 'statistics.typeDescription':
                                                                                type_description = str(stat_value) if stat_value else None
                                        
                                        # Insert planet with complete data
                                        cursor.execute('''
                                            INSERT OR IGNORE INTO Planets (planetId, name, solarSystemId, celestialIndex, typeId, centerX, centerY, centerZ, radius,
                                                                          density, eccentricity, escapeVelocity, surfaceGravity, temperature, pressure,
                                                                          orbitRadius, orbitPeriod, rotationRate, mass, typeDescription)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (planet_id, planet_name, system_id, celestial_index, type_id, position[0], position[1], position[2], radius,
                                              density, eccentricity, escape_velocity, surface_gravity, temperature, pressure,
                                              orbit_radius, orbit_period, rotation_rate, mass, type_description))
                                        planet_count += 1
                                        
                                        # Extract moons and stations for this planet
                                        if isinstance(planet_details, list):
                                            moon_sequence = 0  # Track moon sequence within this planet
                                            for detail in planet_details:
                                                if isinstance(detail, dict):
                                                    for detail_key, detail_value in detail.items():
                                                        # Extract moons
                                                        if detail_key == f'{planet_id}.moons' and isinstance(detail_value, list):
                                                            for moon_info in detail_value:
                                                                if isinstance(moon_info, dict):
                                                                    for moon_key, moon_details in moon_info.items():
                                                                        if moon_key.startswith('moons.'):
                                                                            try:
                                                                                moon_id = int(moon_key.split('.')[-1])
                                                                                moon_sequence += 1  # Increment for each moon in this planet
                                                                                
                                                                                # Generate proper moon name: "SystemName - Planet X - Moon Y"
                                                                                planet_number = int(celestial_index) if celestial_index else planet_id
                                                                                moon_name = f"{system_name} - Planet {planet_number} - Moon {moon_sequence}"
                                                                                
                                                                                # Extract moon data
                                                                                moon_position = [None, None, None]
                                                                                moon_radius = None
                                                                                moon_type_id = None
                                                                                
                                                                                if isinstance(moon_details, list):
                                                                                    for moon_detail in moon_details:
                                                                                        if isinstance(moon_detail, dict):
                                                                                            for moon_detail_key, moon_detail_value in moon_detail.items():
                                                                                                if moon_detail_key == f'{moon_id}.position':
                                                                                                    if isinstance(moon_detail_value, list) and len(moon_detail_value) >= 2:
                                                                                                        vector_data = moon_detail_value[1].get('vector_data', [])
                                                                                                        if len(vector_data) >= 3:
                                                                                                            moon_position = vector_data[:3]
                                                                                                elif moon_detail_key == f'{moon_id}.radius':
                                                                                                    moon_radius = _parse_float(moon_detail_value)
                                                                                
                                                                                # Insert moon
                                                                                cursor.execute('''
                                                                                    INSERT OR IGNORE INTO Moons (moonId, name, planetId, solarSystemId, typeId, centerX, centerY, centerZ, radius)
                                                                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                                                ''', (moon_id, moon_name, planet_id, system_id, moon_type_id, 
                                                                                      moon_position[0], moon_position[1], moon_position[2], moon_radius))
                                                                                moon_count += 1
                                                                            except ValueError:
                                                                                continue
                                                        
                                                        # Extract NPC stations
                                                        elif detail_key == f'{planet_id}.npcStations' and isinstance(detail_value, list):
                                                            for station_info in detail_value:
                                                                if isinstance(station_info, dict):
                                                                    for station_key, station_details in station_info.items():
                                                                        if station_key.startswith('npcStations.'):
                                                                            try:
                                                                                station_id = int(station_key.split('.')[-1])
                                                                                
                                                                                # Extract station data
                                                                                station_name = None
                                                                                station_type_id = None
                                                                                station_owner_id = None
                                                                                station_position = [None, None, None]
                                                                                lagrange_point = None
                                                                                orbit_id = None
                                                                                operation_id = None
                                                                                is_conquerable = None
                                                                                reprocessing_efficiency = None
                                                                                reprocessing_stations_take = None
                                                                                
                                                                                if isinstance(station_details, list):
                                                                                    for station_detail in station_details:
                                                                                        if isinstance(station_detail, dict):
                                                                                            for station_detail_key, station_detail_value in station_detail.items():
                                                                                                if station_detail_key == f'{station_id}.stationName':
                                                                                                    station_name = str(station_detail_value) if station_detail_value else None
                                                                                                elif station_detail_key == f'{station_id}.typeID':
                                                                                                    station_type_id = _parse_float(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.ownerID':
                                                                                                    station_owner_id = _parse_float(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.position':
                                                                                                    if isinstance(station_detail_value, list) and len(station_detail_value) >= 2:
                                                                                                        vector_data = station_detail_value[1].get('vector_data', [])
                                                                                                        if len(vector_data) >= 3:
                                                                                                            station_position = vector_data[:3]
                                                                                                elif station_detail_key == f'{station_id}.lagrangePoint':
                                                                                                    lagrange_point = _parse_float(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.orbitID':
                                                                                                    orbit_id = _parse_float(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.operationID':
                                                                                                    operation_id = _parse_float(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.isConquerable':
                                                                                                    is_conquerable = _parse_bool(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.reprocessingEfficiency':
                                                                                                    reprocessing_efficiency = _parse_float(station_detail_value)
                                                                                                elif station_detail_key == f'{station_id}.reprocessingStationsTake':
                                                                                                    reprocessing_stations_take = _parse_float(station_detail_value)
                                                                                
                                                                                # If no name was found, try localization
                                                                                if not station_name:
                                                                                    station_name = localization_names.get(station_id, f'Station {station_id}')
                                                                                
                                                                                # Insert NPC station
                                                                                cursor.execute('''
                                                                                    INSERT OR IGNORE INTO NpcStations (stationId, name, solarSystemId, planetId, typeId, ownerId, 
                                                                                                                       centerX, centerY, centerZ, lagrangePoint, orbitId, operationId,
                                                                                                                       isConquerable, reprocessingEfficiency, reprocessingStationsTake)
                                                                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                                                ''', (station_id, station_name, system_id, planet_id, station_type_id, station_owner_id,
                                                                                      station_position[0], station_position[1], station_position[2], lagrange_point, orbit_id, operation_id,
                                                                                      is_conquerable, reprocessing_efficiency, reprocessing_stations_take))
                                                                                station_count += 1
                                                                            except ValueError:
                                                                                continue
                                        
                                    except ValueError:
                                        continue
    
    conn.commit()
    print(f"Inserted {planet_count} planets, {moon_count} moons, and {station_count} NPC stations")
    
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
    
    print(f"Successfully created database: {db_path}")
    print("Database contains:")
    print(f"  - {regions_count:,} regions")
    print(f"  - {constellations_count:,} constellations")
    print(f"  - {systems_count:,} systems")
    print(f"  - {jumps_count:,} jump connections")
    print(f"  - {planets_count:,} planets")
    print(f"  - {moons_count:,} moons")
    print(f"  - {stations_count:,} NPC stations")
    
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