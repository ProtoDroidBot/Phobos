"""
Blueprint Query Tool for EVE Frontier/EVE Online Data

Reads blueprint data from industry_blueprints.json and types.json,
providing an easy interface to query manufacturing schemas.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


class BlueprintDB:
    """Query interface for blueprint/schema data"""
    
    def __init__(self, data_dir: str = "output"):
        """
        Initialize the blueprint database.
        
        Args:
            data_dir: Path to output directory containing fsd_built/*.json files
        """
        self.data_dir = Path(data_dir)
        self.blueprints: Dict = {}
        self.types: Dict = {}
        self.groups: Dict = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load blueprint and type data from JSON files"""
        # Load blueprints
        bp_path = self.data_dir / "fsd_built" / "industry_blueprints.json"
        if bp_path.exists():
            with open(bp_path, 'r', encoding='utf-8') as f:
                self.blueprints = json.load(f)
            print(f"Loaded {len(self.blueprints)} blueprints")
        else:
            print(f"Warning: {bp_path} not found")
        
        # Load types
        types_path = self.data_dir / "fsd_built" / "types.json"
        if types_path.exists():
            with open(types_path, 'r', encoding='utf-8') as f:
                self.types = json.load(f)
            print(f"Loaded {len(self.types)} types")
        else:
            print(f"Warning: {types_path} not found")
        
        # Load groups (for category info)
        groups_path = self.data_dir / "fsd_built" / "groups.json"
        if groups_path.exists():
            with open(groups_path, 'r', encoding='utf-8') as f:
                self.groups = json.load(f)
            print(f"Loaded {len(self.groups)} groups")
        else:
            print(f"Warning: {groups_path} not found")
    
    def get_type_name(self, type_id: int, lang: str = "en-us") -> str:
        """Get the name of a type by its ID"""
        type_str = str(type_id)
        if type_str in self.types:
            name_key = f"typeName_{lang}"
            return self.types[type_str].get(name_key, f"Unknown Type {type_id}")
        return f"Unknown Type {type_id}"
    
    def get_group_name(self, group_id: int, lang: str = "en-us") -> str:
        """Get the name of a group by its ID"""
        group_str = str(group_id)
        if group_str in self.groups:
            name_key = f"groupName_{lang}"
            return self.groups[group_str].get(name_key, f"Unknown Group {group_id}")
        return f"Unknown Group {group_id}"
    
    def get_type_category(self, type_id: int) -> Optional[str]:
        """Get the category/group of a type"""
        type_str = str(type_id)
        if type_str in self.types:
            group_id = self.types[type_str].get('groupID')
            if group_id:
                return self.get_group_name(group_id)
        return None
    
    def format_time(self, seconds: int) -> str:
        """Format runtime in seconds to human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s" if secs > 0 else f"{mins}m"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    
    def get_blueprint(self, blueprint_id: int) -> Optional[Dict]:
        """Get a blueprint by its ID"""
        bp_str = str(blueprint_id)
        if bp_str in self.blueprints:
            bp = self.blueprints[bp_str].copy()
            bp['blueprintID'] = blueprint_id
            return bp
        return None
    
    def find_blueprints_by_output(self, type_name: str, exact: bool = False) -> List[Dict]:
        """
        Find all blueprints that produce a specific item.
        
        Args:
            type_name: Name (or partial name) of the output item
            exact: If True, require exact match
        
        Returns:
            List of blueprint dictionaries with enriched data
        """
        results = []
        search_term = type_name.lower()
        
        for bp_id, bp_data in self.blueprints.items():
            primary_type_id = bp_data.get('primaryTypeID')
            if primary_type_id:
                output_name = self.get_type_name(primary_type_id).lower()
                
                if exact:
                    if output_name == search_term:
                        results.append(self._enrich_blueprint(int(bp_id), bp_data))
                else:
                    if search_term in output_name:
                        results.append(self._enrich_blueprint(int(bp_id), bp_data))
        
        return results
    
    def find_blueprints_by_input(self, type_name: str, exact: bool = False) -> List[Dict]:
        """
        Find all blueprints that use a specific material as input.
        
        Args:
            type_name: Name (or partial name) of the input material
            exact: If True, require exact match
        
        Returns:
            List of blueprint dictionaries with enriched data
        """
        results = []
        search_term = type_name.lower()
        
        for bp_id, bp_data in self.blueprints.items():
            for input_item in bp_data.get('inputs', []):
                input_type_id = input_item.get('typeID')
                if input_type_id:
                    input_name = self.get_type_name(input_type_id).lower()
                    
                    if exact:
                        match = input_name == search_term
                    else:
                        match = search_term in input_name
                    
                    if match:
                        results.append(self._enrich_blueprint(int(bp_id), bp_data))
                        break  # Don't add same blueprint multiple times
        
        return results
    
    def _enrich_blueprint(self, bp_id: int, bp_data: Dict) -> Dict:
        """Add human-readable names and data to blueprint"""
        enriched = {
            'blueprintID': bp_id,
            'runTime': bp_data.get('runTime', 0),
            'runTimeFormatted': self.format_time(bp_data.get('runTime', 0)),
            'inputs': [],
            'outputs': []
        }
        
        # Enrich inputs
        for input_item in bp_data.get('inputs', []):
            type_id = input_item['typeID']
            enriched['inputs'].append({
                'typeID': type_id,
                'name': self.get_type_name(type_id),
                'quantity': input_item['quantity'],
                'category': self.get_type_category(type_id)
            })
        
        # Enrich outputs
        for output_item in bp_data.get('outputs', []):
            type_id = output_item['typeID']
            enriched['outputs'].append({
                'typeID': type_id,
                'name': self.get_type_name(type_id),
                'quantity': output_item['quantity'],
                'category': self.get_type_category(type_id)
            })
        
        # Add primary output info
        primary_type_id = bp_data.get('primaryTypeID')
        if primary_type_id:
            enriched['primaryOutput'] = {
                'typeID': primary_type_id,
                'name': self.get_type_name(primary_type_id),
                'category': self.get_type_category(primary_type_id)
            }
        
        return enriched
    
    def print_blueprint(self, bp: Dict, verbose: bool = False):
        """Pretty-print a blueprint in a readable format"""
        primary = bp.get('primaryOutput', {})
        print(f"\n{'='*70}")
        print(f"Blueprint ID: {bp['blueprintID']}")
        print(f"Product: {primary.get('name', 'Unknown')}")
        if verbose and primary.get('category'):
            print(f"Category: {primary.get('category')}")
        print(f"Run Time: {bp['runTimeFormatted']}")
        print(f"\nInputs:")
        for item in bp['inputs']:
            category_str = f" ({item['category']})" if verbose and item.get('category') else ""
            print(f"  • {item['name']:<40} {item['quantity']:>6}{category_str}")
        
        print(f"\nOutputs:")
        for item in bp['outputs']:
            category_str = f" ({item['category']})" if verbose and item.get('category') else ""
            print(f"  • {item['name']:<40} {item['quantity']:>6}{category_str}")
        print(f"{'='*70}")
    
    def search(self, query: str, search_type: str = "all", exact: bool = False, 
               verbose: bool = False, limit: Optional[int] = None):
        """
        Search for blueprints.
        
        Args:
            query: Search term
            search_type: One of "all", "output", "input"
            exact: Require exact name match
            verbose: Show additional details
            limit: Maximum number of results to show
        """
        results = []
        
        if search_type in ("all", "output"):
            results.extend(self.find_blueprints_by_output(query, exact))
        
        if search_type in ("all", "input"):
            input_results = self.find_blueprints_by_input(query, exact)
            # Avoid duplicates
            existing_ids = {bp['blueprintID'] for bp in results}
            results.extend([bp for bp in input_results if bp['blueprintID'] not in existing_ids])
        
        if not results:
            print(f"No blueprints found for '{query}'")
            return []
        
        print(f"\nFound {len(results)} blueprint(s) matching '{query}':")
        
        if limit:
            results = results[:limit]
            print(f"(Showing first {limit})")
        
        for bp in results:
            self.print_blueprint(bp, verbose)
        
        return results


def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query EVE blueprint/schema data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for blueprints that produce ammo
  python query_blueprints.py --output "ammo"
  
  # Search for blueprints using iron
  python query_blueprints.py --input "iron"
  
  # Search everywhere for "gyrojet"
  python query_blueprints.py --search "gyrojet"
  
  # Get specific blueprint by ID
  python query_blueprints.py --id 1000
  
  # Exact match only
  python query_blueprints.py --output "Leap" --exact
        """
    )
    
    parser.add_argument('--data-dir', default='output',
                       help='Path to output directory (default: output)')
    parser.add_argument('--search', '-s', metavar='QUERY',
                       help='Search blueprints (inputs and outputs)')
    parser.add_argument('--output', '-o', metavar='ITEM',
                       help='Find blueprints that produce this item')
    parser.add_argument('--input', '-i', metavar='MATERIAL',
                       help='Find blueprints that use this material')
    parser.add_argument('--id', type=int, metavar='ID',
                       help='Get blueprint by ID')
    parser.add_argument('--exact', '-e', action='store_true',
                       help='Require exact name match')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show additional details')
    parser.add_argument('--limit', '-l', type=int, metavar='N',
                       help='Limit number of results')
    
    args = parser.parse_args()
    
    # Initialize database
    db = BlueprintDB(args.data_dir)
    
    # Handle queries
    if args.id:
        bp_data = db.get_blueprint(args.id)
        if bp_data:
            enriched = db._enrich_blueprint(args.id, bp_data)
            db.print_blueprint(enriched, args.verbose)
        else:
            print(f"Blueprint ID {args.id} not found")
            sys.exit(1)
    
    elif args.output:
        db.search(args.output, search_type="output", exact=args.exact, 
                 verbose=args.verbose, limit=args.limit)
    
    elif args.input:
        db.search(args.input, search_type="input", exact=args.exact,
                 verbose=args.verbose, limit=args.limit)
    
    elif args.search:
        db.search(args.search, search_type="all", exact=args.exact,
                 verbose=args.verbose, limit=args.limit)
    
    else:
        parser.print_help()
        print(f"\nDatabase loaded: {len(db.blueprints)} blueprints, {len(db.types)} types")


if __name__ == "__main__":
    main()
