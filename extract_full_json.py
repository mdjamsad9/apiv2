"""
extract_full_json.py
Extract full JSON arrays from the Crexify TV memory dump.
We know the decrypted events JSON is around offset 12,680,000.
Search wider around that region and also look for event_cats and categories.
"""
import sys
import json
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

DUMP_FILE = "dump_new.bin"
OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

print(f"Reading {DUMP_FILE}...")
with open(DUMP_FILE, "rb") as f:
    data = f.read()
print(f"Loaded {len(data):,} bytes")

def try_extract_json_at(data, offset, max_size=5_000_000):
    """Try to extract a complete JSON value starting at offset."""
    chunk = data[offset:offset + max_size]
    try:
        text = chunk.decode('utf-8', errors='replace')
    except Exception:
        return None
    
    if not (text.startswith('[') or text.startswith('{')):
        return None
    
    bracket = text[0]
    close = ']' if bracket == '[' else '}'
    depth = 0
    for i, c in enumerate(text):
        if c == bracket:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                json_str = text[:i+1]
                try:
                    parsed = json.loads(json_str)
                    return parsed, json_str
                except Exception:
                    return None
    return None

# Find all [ and { starting points in a wide region
SEARCH_REGION_START = 12_600_000
SEARCH_REGION_END   = 12_800_000

print(f"\nSearching region {SEARCH_REGION_START:,} to {SEARCH_REGION_END:,}...")
region = data[SEARCH_REGION_START:SEARCH_REGION_END]

# Find positions of large JSON arrays
found = {}

i = 0
while i < len(region):
    if region[i] in [ord('['), ord('{')]:
        abs_offset = SEARCH_REGION_START + i
        result = try_extract_json_at(data, abs_offset)
        if result:
            parsed, json_str = result
            size = len(json_str)
            if size > 1000:
                key = f"{abs_offset}_{size}"
                if key not in found:
                    found[key] = (abs_offset, parsed, size)
                    print(f"  Found JSON at offset {abs_offset:,}: type={type(parsed).__name__}, "
                          f"items={len(parsed) if isinstance(parsed, list) else 'dict'}, "
                          f"size={size:,}")
                i += size  # skip past this JSON
                continue
    i += 1

print(f"\nFound {len(found)} large JSON structures")

# Categorize and save
events_arr = None
categories_arr = None
event_cats_arr = None

for key, (offset, parsed, size) in sorted(found.items(), key=lambda x: -x[1][2]):
    sample = str(parsed)[:200]
    print(f"\n--- Offset {offset:,}, size {size:,} ---")
    print(f"  Preview: {sample[:200]}")
    
    # Identify type
    if isinstance(parsed, list) and len(parsed) > 0:
        first = parsed[0]
        if isinstance(first, dict):
            keys = set(first.keys())
            if 'teamAName' in keys or 'eventName' in keys or 'start_date' in keys:
                print("  → IDENTIFIED AS: events list")
                if events_arr is None or size > len(str(events_arr)):
                    events_arr = parsed
            elif 'categoryLogo' in keys or 'cat_name' in keys or 'categoryId' in keys:
                print("  → IDENTIFIED AS: categories list")
                if categories_arr is None or size > len(str(categories_arr)):
                    categories_arr = parsed
            elif 'id' in keys and ('name' in keys or 'catId' in keys):
                print("  → IDENTIFIED AS: event_cats list")
                if event_cats_arr is None or size > len(str(event_cats_arr)):
                    event_cats_arr = parsed

# Save identified arrays
if events_arr:
    out = os.path.join(OUT_DIR, "events.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(events_arr, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved events.json ({len(events_arr)} events)")
    
if categories_arr:
    out = os.path.join(OUT_DIR, "categories.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(categories_arr, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved categories.json ({len(categories_arr)} categories)")
    
if event_cats_arr:
    out = os.path.join(OUT_DIR, "event_cats.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(event_cats_arr, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved event_cats.json ({len(event_cats_arr)} event cats)")

# Also look for the FULL large array that contains all events (search further)
print("\n--- Searching for larger arrays (full datasets) ---")
# Look for the biggest JSON arrays in the whole dump
markers = []
for pattern in [b'[{"visible"', b'[{"id"', b'[{"categoryLogo"', b'[{"cat_', b'[{"name"']:
    pos = 0
    while True:
        idx = data.find(pattern, pos)
        if idx == -1:
            break
        markers.append(idx)
        pos = idx + 1

print(f"Found {len(markers)} potential array starts")
for idx in markers:
    result = try_extract_json_at(data, idx)
    if result:
        parsed, json_str = result
        size = len(json_str)
        if isinstance(parsed, list) and len(parsed) > 5:
            print(f"\n  Offset {idx:,}: {len(parsed)} items, {size:,} bytes")
            print(f"  Preview: {json_str[:200]}")
            fname = f"full_array_{idx}.json"
            with open(os.path.join(OUT_DIR, fname), 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            print(f"  → Saved {fname}")
