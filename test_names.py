#!/usr/bin/env python3

import sqlite3

def test_localized_names():
    conn = sqlite3.connect('eve_universe.db')
    cursor = conn.cursor()

    # Look for system ID 30009299 (should be I4F-MCH now)
    cursor.execute('SELECT system_id, name FROM systems WHERE system_id = 30009299')
    result = cursor.fetchone()
    if result:
        print(f'Found system 30009299: ID={result[0]}, Name="{result[1]}"')
    else:
        print('System 30009299 not found')

    # Check for I4F-MCH by name
    cursor.execute('SELECT system_id, name, constellation_id FROM systems WHERE name = ?', ('I4F-MCH',))
    result = cursor.fetchone()
    if result:
        print(f'Found I4F-MCH: {result}')
    else:
        print('I4F-MCH not found by name')

    # Show some sample systems to see the names
    cursor.execute('SELECT system_id, name FROM systems LIMIT 10')
    print('\nSample systems with localized names:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')

    # Count how many systems have real names vs generic names
    cursor.execute('SELECT COUNT(*) FROM systems WHERE name NOT LIKE ?', ('System %',))
    named_systems = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM systems')
    total_systems = cursor.fetchone()[0]
    print(f'\nSystems with real names: {named_systems} out of {total_systems}')

    # Show some sample regions
    cursor.execute('SELECT region_id, name FROM regions LIMIT 5')
    print('\nSample regions:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')

    # Show some sample constellations
    cursor.execute('SELECT constellation_id, name FROM constellations LIMIT 5')
    print('\nSample constellations:')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')

    conn.close()

if __name__ == '__main__':
    test_localized_names()