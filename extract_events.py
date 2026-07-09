"""
extract_events.py
Parse events.json and event_cats.json from the extracted memory region.
"""
import sys, json, os, re

sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

with open("region.bin", "rb") as f:
    data = f.read()

print(f"Region size: {len(data):,} bytes")

# Decode as UTF-8
text = data.decode('utf-8', errors='replace')

# Find all valid JSON objects starting with {"visible"
events = []
cats = []

pos = 0
while True:
    idx = text.find('{"', pos)
    if idx == -1:
        break
    
    # Try to parse a JSON object here
    depth = 0
    in_str = False
    escape = False
    end_pos = -1
    
    for i in range(idx, min(len(text), idx + 50000)):
        c = text[i]
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
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end_pos = i + 1
                break
    
    if end_pos > idx + 100:
        snippet = text[idx:end_pos]
        try:
            obj = json.loads(snippet)
            if isinstance(obj, dict):
                if 'visible' in obj or 'eventName' in obj or 'teamAName' in obj:
                    events.append(obj)
                elif 'categoryLogo' in obj:
                    cats.append(obj)
        except Exception:
            pass
        pos = end_pos
    else:
        pos = idx + 1

print(f"\nFound {len(events)} event objects")
print(f"Found {len(cats)} category objects")

if events:
    # Sort by priority
    events.sort(key=lambda e: (e.get('priority', 99), e.get('eventName', '')))
    out = os.path.join(OUT_DIR, "events.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved events.json ({len(events)} events)")
    print("  Sample:", json.dumps(events[0], ensure_ascii=False)[:200])

if cats:
    out = os.path.join(OUT_DIR, "event_cats.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(cats, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved event_cats.json ({len(cats)} event cats)")
    print("  Sample:", json.dumps(cats[0], ensure_ascii=False)[:200])

# Also look for channels data in the region
channels = {}
channel_pattern = re.compile(r'"channel_name"\s*:\s*"([^"]+)"')
link_pattern = re.compile(r'"link"\s*:\s*"([^"]+)"')
matches = channel_pattern.findall(text)
print(f"\nFound {len(matches)} channel names in region:")
for m in matches[:10]:
    print(f"  {m}")
