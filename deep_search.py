"""
deep_search.py
Deep search the Crexify TV memory dump for the FULL JSON arrays.
The individual event objects are around offset 12.68M but those seem to be
parsed fragments. The original response (as a string) should exist somewhere.
"""
import sys
import json
import os

sys.stdout.reconfigure(encoding='utf-8')

DUMP_FILE = "dump_new.bin"
OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

print(f"Reading {DUMP_FILE}...")
with open(DUMP_FILE, "rb") as f:
    data = f.read()
print(f"Loaded {len(data):,} bytes\n")

def extract_json_from(data, offset, max_size=20_000_000):
    chunk = data[offset:offset + max_size]
    text = chunk.decode('utf-8', errors='replace')
    bracket = text[0] if text else ''
    if bracket not in '[{':
        return None
    close = ']' if bracket == '[' else '}'
    depth = 0
    in_str = False
    escape = False
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if c == '\\' and in_str:
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == bracket:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                json_str = text[:i+1]
                try:
                    parsed = json.loads(json_str)
                    return parsed, len(json_str)
                except json.JSONDecodeError:
                    return None
    return None

# Search patterns that would indicate the start of each JSON dataset
search_pairs = [
    # events list
    (b'"visible"', "events"),
    # categories / event_cats
    (b'"categoryLogo"', "event_cats_or_categories"),
    (b'"catId"', "event_cats"),
]

print("Doing fast pattern search across entire dump...")

saved = set()

for pattern, label in search_pairs:
    print(f"\nSearching for: {pattern} ({label})")
    pos = 0
    count = 0
    while True:
        idx = data.find(pattern, pos)
        if idx == -1:
            break
        pos = idx + 1
        count += 1
        
        # Look backward for the start of the JSON array/object
        # Check up to 50KB back for a '[' or '{'
        look_back = min(idx, 200_000)
        chunk_before = data[idx - look_back: idx + 1]
        # Find last '[' before this pattern
        last_bracket = -1
        for j in range(len(chunk_before) - 1, -1, -1):
            if chunk_before[j] == ord('[') or chunk_before[j] == ord('{'):
                last_bracket = idx - look_back + j
                break
        
        if last_bracket == -1:
            continue
        
        # Try to extract full JSON from this position
        start = last_bracket
        if start in saved:
            continue
        
        result = extract_json_from(data, start)
        if result:
            parsed, size = result
            if isinstance(parsed, list) and len(parsed) > 3 and size > 2000:
                saved.add(start)
                print(f"  ✓ Found array at {start:,}: {len(parsed)} items, {size:,} bytes")
                preview = str(parsed[0])[:200] if parsed else ''
                print(f"    First item: {preview}")
                
                # Identify what type of data this is
                fname = None
                if isinstance(parsed[0], dict):
                    keys = set(parsed[0].keys())
                    if 'visible' in keys or 'teamAName' in keys or 'eventName' in keys:
                        fname = "events.json"
                    elif 'categoryLogo' in keys:
                        fname = "event_cats.json"
                    elif 'catId' in keys or ('id' in keys and 'name' in keys and len(keys) <= 5):
                        fname = "categories.json"
                
                if fname:
                    outpath = os.path.join(OUT_DIR, fname)
                    with open(outpath, 'w', encoding='utf-8') as f:
                        json.dump(parsed, f, indent=2, ensure_ascii=False)
                    print(f"    → Saved as {fname}")
                else:
                    # Save with generic name
                    generic = os.path.join(OUT_DIR, f"array_{start}.json")
                    with open(generic, 'w', encoding='utf-8') as f:
                        json.dump(parsed, f, indent=2, ensure_ascii=False)
                    print(f"    → Saved as array_{start}.json (unknown type)")

print("\nDone!")
# List saved files
for f in sorted(os.listdir(OUT_DIR)):
    fpath = os.path.join(OUT_DIR, f)
    print(f"  {f}: {os.path.getsize(fpath):,} bytes")
