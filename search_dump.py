"""
search_dump.py
Search the Crexify TV memory dump for decrypted JSON payloads.
"""
import sys
import re
import json
import os

sys.stdout.reconfigure(encoding='utf-8')

DUMP_FILE = "dump_new.bin"
OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

# JSON patterns to search for
PATTERNS = [
    # event_cats / events list
    b'[{"id"',
    b'[{ "id"',
    b'{"id":',
    # categories
    b'"categoryLogo"',
    b'"cat_name"',
    b'"cat_logo"',
    # events specific
    b'"teamAName"',
    b'"teamBName"',
    b'"eventLogo"',
    b'"start_date"',
    b'"start_time"',
    b'"live"',
    # channels
    b'"stream_url"',
    b'"channel_name"',
    b'"link"',
]

print(f"Reading dump: {DUMP_FILE} ({os.path.getsize(DUMP_FILE):,} bytes)...")

with open(DUMP_FILE, "rb") as f:
    data = f.read()

print(f"Loaded {len(data):,} bytes into memory.")
print("\nSearching for JSON patterns...")

found_offsets = set()

for pattern in PATTERNS:
    pos = 0
    while True:
        idx = data.find(pattern, pos)
        if idx == -1:
            break
        # Round down to nearest 256 bytes to group nearby finds
        bucket = idx // 256
        if bucket not in found_offsets:
            found_offsets.add(bucket)
        pos = idx + 1

print(f"Found {len(found_offsets)} candidate memory regions.")

# For each region, try to extract JSON
extracted = []
for bucket in sorted(found_offsets):
    start = max(0, bucket * 256 - 512)
    end = min(len(data), bucket * 256 + 8192)
    chunk = data[start:end]
    
    # Try UTF-8 decode
    try:
        text = chunk.decode('utf-8', errors='ignore')
    except Exception:
        continue
    
    # Find JSON array or object in the text
    for bracket in ['[', '{']:
        bi = text.find(bracket)
        while bi != -1:
            candidate = text[bi:]
            # Try to parse up to 200KB
            for length in [500, 2000, 10000, 50000, 100000]:
                snippet = candidate[:length]
                # Count brackets to see if balanced
                opens = snippet.count(bracket)
                closes = snippet.count(']' if bracket == '[' else '}')
                if opens > 0 and closes >= opens * 0.8:
                    try:
                        # Find the closing bracket position
                        close_char = ']' if bracket == '[' else '}'
                        depth = 0
                        end_pos = -1
                        for i, c in enumerate(snippet):
                            if c == bracket:
                                depth += 1
                            elif c == close_char:
                                depth -= 1
                                if depth == 0:
                                    end_pos = i + 1
                                    break
                        if end_pos > 100:
                            json_str = snippet[:end_pos]
                            parsed = json.loads(json_str)
                            if isinstance(parsed, (list, dict)) and len(str(parsed)) > 200:
                                key = json_str[:100]
                                if key not in [e.get('_key', '') for e in extracted]:
                                    extracted.append({'_key': key, '_offset': start + bi, 'data': parsed})
                                    print(f"\n[FOUND JSON] offset={start + bi:,}, type={type(parsed).__name__}, len={len(str(parsed))}")
                                    preview = json_str[:300]
                                    print(f"  Preview: {repr(preview)}")
                    except Exception:
                        pass
            bi = text.find(bracket, bi + 1)

print(f"\n{'='*60}")
print(f"Total JSON objects extracted: {len(extracted)}")

# Save extracted JSONs
for i, item in enumerate(extracted):
    fname = f"mem_extract_{i+1}.json"
    with open(os.path.join(OUT_DIR, fname), 'w', encoding='utf-8') as f:
        json.dump(item['data'], f, indent=2, ensure_ascii=False)
    print(f"Saved: {fname} (offset {item['_offset']:,})")

print("\nDone.")
