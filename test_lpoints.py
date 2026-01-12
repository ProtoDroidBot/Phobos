#!/usr/bin/env python3
"""Test script to verify Lagrange Points extraction from solarsystemcontent.json"""

import json
from pathlib import Path

# Load the data
phobos_path = Path("output")
systems_content_path = phobos_path / 'fsd_binary_schema' / 'solarsystemcontent.json'

with open(systems_content_path, 'r', encoding='utf-8') as f:
    systems_content_data = json.load(f)

if 'Type: FSD Multi Index' in systems_content_data:
    systems_content_data = systems_content_data['Type: FSD Multi Index']

lpoint_count = 0
sample_lpoints = []

# Process first 100 systems
for i, system_dict in enumerate(systems_content_data[:100]):
    for system_id_str, system_data in system_dict.items():
        try:
            system_id = int(system_id_str)
        except ValueError:
            continue
        
        # Only process dict entries
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
                                
                                lpoint_count += 1
                                if len(sample_lpoints) < 10:
                                    sample_lpoints.append({
                                        'system_id': system_id,
                                        'planet_id': planet_id,
                                        'type': point_type,
                                        'position': (x, y, z)
                                    })
                            except (ValueError, TypeError) as e:
                                print(f"Error parsing L-point: {e}")

print(f"Found {lpoint_count} Lagrange Points in first 100 systems")
print("\nSample L-Points:")
for lp in sample_lpoints:
    print(f"  System {lp['system_id']}, Planet {lp['planet_id']}, {lp['type']}: ({lp['position'][0]:.2e}, {lp['position'][1]:.2e}, {lp['position'][2]:.2e})")
