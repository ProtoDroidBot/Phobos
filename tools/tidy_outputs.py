"""
Tidy Phobos JSON outputs by removing keys that are constant across all entries
or duplicated (always equal to another key) across all entries.

Produces cleaned JSON files under `output_cleaned/<miner>/<file>.json`.

Usage:
    python tools/tidy_outputs.py --input output --output output_cleaned --dry-run

Options:
  --input PATH     Path to Phobos output directory (default: output)
  --output PATH    Path to write cleaned output (default: output_cleaned)
  --dry-run        Don't write files; only report what would be removed
  --min-count N    Minimum number of entries before analyzing duplicates (default: 2)

Behavior notes:
- Supports top-level dict of dicts (id->object) and list of objects.
- Preserves original top-level structure when writing cleaned files.
- Skips files that are not JSON objects containing dict entries.

Safety: The script writes to a separate folder by default to avoid overwriting original exports.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def analyze_entries(entries: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Return (constant_keys, duplicate_keys_to_remove)

    - constant_keys: keys whose value is identical across all entries
    - duplicate_keys_to_remove: keys that are strictly equal to another key for all entries
    """
    if not entries:
        return [], []

    # collect keys present in every entry
    keys = set(entries[0].keys())
    for e in entries[1:]:
        keys &= set(e.keys())
    if not keys:
        return [], []

    # constant keys
    constant_keys = []
    key_values = {}
    for k in keys:
        vals = set()
        for e in entries:
            vals.add(json.dumps(e.get(k, None), sort_keys=True))
            if len(vals) > 1:
                break
        if len(vals) == 1:
            constant_keys.append(k)
        key_values[k] = vals

    # duplicates: find keys B where exists key A != B such that for all entries A==B
    duplicate_keys_to_remove = []
    keys_list = sorted(keys)
    for i, a in enumerate(keys_list):
        for b in keys_list[i+1:]:
            all_equal = True
            for e in entries:
                va = e.get(a, None)
                vb = e.get(b, None)
                if va != vb:
                    all_equal = False
                    break
            if all_equal:
                # mark the later key (b) for removal to keep a stable choice
                if b not in duplicate_keys_to_remove:
                    duplicate_keys_to_remove.append(b)
    return constant_keys, duplicate_keys_to_remove


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def process_file(in_path: Path, out_path: Path, dry_run: bool=False, min_count:int=2):
    try:
        data = load_json(in_path)
    except Exception as e:
        return (str(in_path), False, f"failed to load JSON: {e}", [])

    # Determine entries list and structure
    if isinstance(data, dict):
        # check if dict of dicts with non-numeric keys -> treat values as entries
        values = list(data.values())
        if all(isinstance(v, dict) for v in values) and len(values) >= min_count:
            entries = values
            is_mapping = True
        else:
            # not suitable structure
            return (str(in_path), False, "skipped (not dict-of-dicts with sufficient entries)", [])
    elif isinstance(data, list):
        if all(isinstance(v, dict) for v in data) and len(data) >= min_count:
            entries = data
            is_mapping = False
        else:
            return (str(in_path), False, "skipped (not list-of-dicts with sufficient entries)", [])
    else:
        return (str(in_path), False, "skipped (unsupported top-level JSON type)", [])

    constant_keys, dup_keys = analyze_entries(entries)
    remove_keys = set(constant_keys) | set(dup_keys)

    if not remove_keys:
        return (str(in_path), True, "no removable keys found", [])

    # Apply removals
    cleaned_entries = []
    for e in entries:
        new_e = {k: v for k, v in e.items() if k not in remove_keys}
        cleaned_entries.append(new_e)

    # Build output structure matching original
    if is_mapping:
        # preserve original keys mapping
        new_data = {}
        for orig_k, orig_v in data.items():
            if isinstance(orig_v, dict):
                new_data[orig_k] = {k: v for k, v in orig_v.items() if k not in remove_keys}
            else:
                new_data[orig_k] = orig_v
    else:
        new_data = cleaned_entries

    if not dry_run:
        write_json(new_data, out_path)

    removed = sorted(remove_keys)
    return (str(in_path), True, f"removed {len(removed)} keys", removed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', default='output', help='Path to Phobos output directory')
    parser.add_argument('--output', '-o', default='output_cleaned', help='Path to write cleaned output')
    parser.add_argument('--dry-run', action='store_true', help='Do not write files, only report')
    parser.add_argument('--min-count', type=int, default=2, help='Minimum number of entries before analyzing file')
    parser.add_argument('--max-size-mb', type=int, default=50, help='Skip files larger than this size (MB)')
    args = parser.parse_args()

    in_root = Path(args.input)
    out_root = Path(args.output)
    if not in_root.exists():
        print(f"Input path not found: {in_root}")
        return

    results = []
    for miner_dir in sorted([p for p in in_root.iterdir() if p.is_dir()]):
        for json_file in sorted(miner_dir.glob('*.json')):
            rel = json_file.relative_to(in_root)
            out_file = out_root / rel
            # Skip files that are too large to safely load into memory
            try:
                size_mb = json_file.stat().st_size / (1024 * 1024)
            except Exception:
                size_mb = 0
            if args.max_size_mb and size_mb > args.max_size_mb:
                print(f"SKIP-LARGE: {json_file} -> size {size_mb:.1f} MB exceeds max {args.max_size_mb} MB")
                results.append((str(json_file), False, f"skipped (file too large: {size_mb:.1f} MB)", []))
                continue
            info = process_file(json_file, out_file, dry_run=args.dry_run, min_count=args.min_count)
            results.append(info)
            path, ok, msg, removed = info
            if ok:
                print(f"OK: {path} -> {msg}; removed: {removed}")
            else:
                print(f"SKIP: {path} -> {msg}")

    # Summary
    total = len(results)
    cleaned = sum(1 for r in results if r[1] and r[3])
    skipped = total - cleaned
    print(f"\nProcessed {total} files; cleaned {cleaned}; skipped {skipped}")

if __name__ == '__main__':
    main()
