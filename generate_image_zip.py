#!/usr/bin/env python3
"""
Extract item icons from EVE client and package them into a zip file.

This script:
1. Reads types.json to get all typeID -> iconID/graphicID mappings
2. Reads iconids.json to get iconID -> iconFile (res:/ path) mappings
3. Reads graphicids.json to get graphicID -> iconInfo.folder mappings (ships/structures)
4. Uses ResourceBrowser to fetch actual image files from the EVE client (case-insensitive path lookup)
5. Creates a zip file with images named NNNN.png (where NNNN is typeID)
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

from util.resource_browser import ResourceBrowser


def load_types(output_path):
    """Load types data from output directory."""
    types_path = os.path.join(output_path, 'fsd_built', 'types.json')
    if not os.path.exists(types_path):
        raise FileNotFoundError(f"types.json not found at {types_path}. Run 'python run.py' first to extract data.")
    
    print(f"Loading types from {types_path}...")
    with open(types_path, 'r', encoding='utf-8') as f:
        types_data = json.load(f)
    print(f"Loaded {len(types_data)} types")
    return types_data


def load_iconids(output_path):
    """Load icon ID mappings from output directory."""
    iconids_path = os.path.join(output_path, 'fsd_built', 'iconids.json')
    if not os.path.exists(iconids_path):
        raise FileNotFoundError(f"iconids.json not found at {iconids_path}. Run 'python run.py' first to extract data.")
    
    print(f"Loading icon mappings from {iconids_path}...")
    with open(iconids_path, 'r', encoding='utf-8') as f:
        iconids_data = json.load(f)
    print(f"Loaded {len(iconids_data)} icon mappings")
    return iconids_data


def load_graphicids(output_path):
    """Load graphic ID mappings from output directory."""
    graphicids_path = os.path.join(output_path, 'fsd_built', 'graphicids.json')
    if not os.path.exists(graphicids_path):
        raise FileNotFoundError(
            f"graphicids.json not found at {graphicids_path}. Run 'python run.py' first to extract data.")

    print(f"Loading graphic mappings from {graphicids_path}...")
    with open(graphicids_path, 'r', encoding='utf-8') as f:
        graphicids_data = json.load(f)
    print(f"Loaded {len(graphicids_data)} graphic mappings")
    return graphicids_data


def _sof_icon_candidates(graphic_id, folder):
    # In Stillness / Frontier, ship/structure icons commonly live in SOF folders as:
    #   <folder>/<graphicID>_64.png, <graphicID>_128.png, ...
    # Return candidates in descending order of size to prefer high-res.
    candidates = []
    
    # 512 - try PNG then JPG
    candidates.append(f"{folder}/{graphic_id}_512.png")
    candidates.append(f"{folder}/{graphic_id}_512.jpg")

    # 256, 128, 64
    for size in (256, 128, 64):
        candidates.append(f"{folder}/{graphic_id}_{size}.png")
    
    return candidates


def build_type_icon_candidates(types_data, iconids_data, graphicids_data):
    """Build a map of typeID -> list of candidate resource paths."""
    type_candidates = {}
    no_iconid = 0
    no_graphicid = 0
    missing_iconid_map = 0
    missing_graphicid_map = 0

    for type_id, type_info in types_data.items():
        # Filter: Only extract icons for published types with mass > 0
        if not type_info.get('published'):
            continue
        if type_info.get('mass', 0) <= 0:
            continue

        candidates = []

        # 1. Try GraphicID first (High-res Renders for ships/structures)
        graphic_id = type_info.get('graphicID')
        if graphic_id is None:
            no_graphicid += 1
        else:
            graphic_info = graphicids_data.get(str(graphic_id))
            if graphic_info is None:
                missing_graphicid_map += 1
            else:
                icon_info = graphic_info.get('iconInfo')
                if isinstance(icon_info, dict):
                    folder = icon_info.get('folder')
                    if folder:
                        candidates.extend(_sof_icon_candidates(str(graphic_id), folder))

        # 2. Try IconID second (Standard UI icons, usually 64px)
        icon_id = type_info.get('iconID')
        if icon_id is None:
            no_iconid += 1
        else:
            icon_info = iconids_data.get(str(icon_id))
            if icon_info is None:
                missing_iconid_map += 1
            else:
                icon_file = icon_info.get('iconFile')
                if icon_file:
                    candidates.append(icon_file)

        if candidates:
            type_candidates[type_id] = candidates

    print(f"Built icon candidates: {len(type_candidates)} types with icon candidates")
    if no_iconid > 0:
        print(f"  {no_iconid} types have no iconID field")
    if no_graphicid > 0:
        print(f"  {no_graphicid} types have no graphicID field")
    if missing_iconid_map > 0:
        print(f"  {missing_iconid_map} types have iconID but no matching icon mapping")
    if missing_graphicid_map > 0:
        print(f"  {missing_graphicid_map} types have graphicID but no matching graphic mapping")

    return type_candidates


def extract_icons_to_zip(type_candidates, resource_browser, output_zip_path, verbose=False):
    """Extract icon files and write them to a zip file."""
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    
    successful = 0
    failed = 0
    first_errors = []
    
    # Make resource lookup case-insensitive because some extracted metadata uses different casing
    # than the actual indexed file paths.
    resource_index = resource_browser._resource_index
    index_lc = {k.lower(): k for k in resource_index.keys()}

    print(f"Extracting {len(type_candidates)} icons to {output_zip_path}...")
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for type_id, candidates in sorted(type_candidates.items(), key=lambda x: int(x[0])):
            try:
                resolved_path = None
                for candidate in candidates:
                    actual = index_lc.get(candidate.lower())
                    if actual is not None:
                        resolved_path = actual
                        break

                if resolved_path is None:
                    raise KeyError(candidates[0])

                # Fetch icon data from EVE client
                data = resource_browser.get_file_data(resolved_path)
                
                # Write to zip with typeID as filename
                zip_filename = f"{type_id}.png"
                # Keep extension .png as requested; most ship/structure icons are PNGs.
                zf.writestr(zip_filename, data)
                
                successful += 1
                if verbose and successful % 250 == 0:
                    print(f"  Processed {successful}/{len(type_candidates)} icons...")
                    
            except Exception as e:
                failed += 1
                if len(first_errors) < 3:
                    first_errors.append((type_id, candidates[0], str(e)))
                if verbose:
                    print(f"  Failed to extract icon for type {type_id} ({candidates[0]}): {e}")
    
    # Always show first few errors to help debugging
    if first_errors and not verbose:
        print(f"\nFirst {len(first_errors)} errors:")
        for type_id, icon_path, error in first_errors:
            print(f"  Type {type_id} ({icon_path}): {error}")
    
    print(f"Completed: {successful} icons extracted, {failed} failed")
    return successful, failed


def main():
    parser = argparse.ArgumentParser(
        description='Extract EVE item icons and package them into a zip file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract icons from EVE Frontier (default)
  python generate_image_zip.py --eve "C:\\CCP\\EVE Frontier"
  
  # Extract icons from EVE Online
  python generate_image_zip.py --eve "C:\\CCP\\EVE Online" --server tq
  
  # Specify custom output directories
  python generate_image_zip.py --eve "C:\\CCP\\EVE Frontier" --output output --zip icons.zip
  
  # Enable verbose output
  python generate_image_zip.py --eve "C:\\CCP\\EVE Frontier" --verbose
"""
    )
    
    parser.add_argument(
        '--eve',
        required=True,
        help='Path to EVE client installation directory'
    )
    
    parser.add_argument(
        '--server',
        default='stillness',
        help='Server alias (stillness for EVE Frontier, tq/sisi for EVE Online). Default: stillness'
    )
    
    parser.add_argument(
        '--output',
        default='output',
        help='Path to Phobos output directory (where types.json/iconids.json/graphicids.json are). Default: output'
    )
    
    parser.add_argument(
        '--zip',
        default='output/zip/item_icons.zip',
        help='Output zip file path. Default: output/zip/item_icons.zip'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate EVE path
    if not os.path.isdir(args.eve):
        print(f"Error: EVE installation directory not found: {args.eve}", file=sys.stderr)
        return 1
    
    # Validate output path
    if not os.path.isdir(args.output):
        print(f"Error: Output directory not found: {args.output}", file=sys.stderr)
        print("Run 'python run.py' first to extract game data.", file=sys.stderr)
        return 1
    
    try:
        # Load data files
        types_data = load_types(args.output)
        iconids_data = load_iconids(args.output)
        graphicids_data = load_graphicids(args.output)
        
        # Build type -> candidate icon paths
        type_candidates = build_type_icon_candidates(types_data, iconids_data, graphicids_data)
        
        if not type_candidates:
            print("Error: No valid type-to-icon mappings found", file=sys.stderr)
            return 1
        
        # Initialize resource browser
        print(f"Initializing resource browser for EVE path: {args.eve}")
        resource_browser = ResourceBrowser(args.eve, args.server)
        
        # Extract icons to zip
        successful, failed = extract_icons_to_zip(
            type_candidates,
            resource_browser,
            args.zip,
            verbose=args.verbose
        )
        
        if successful == 0:
            print("Error: No icons were successfully extracted", file=sys.stderr)
            return 1
        
        print(f"\nSuccess! Zip file created: {args.zip}")
        print(f"File size: {os.path.getsize(args.zip) / (1024 * 1024):.2f} MB")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
