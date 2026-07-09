"""
extract_all.py  - Extract events, event_cats, and categories from memory regions.
"""
import sys, json, os

sys.stdout.reconfigure(encoding='utf-8')
OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

def extract_json_objects(filename, keywords, label):
    print(f"\n=== Extracting {label} from {filename} ===")
    with open(filename, "rb") as f:
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    
    objects = []
    seen = set()
    pos = 0
    
    while True:
        idx = text.find('{"', pos)
        if idx == -1:
            break
        
        depth = 0; in_str = False; escape = False; end_pos = -1
        for i in range(idx, min(len(text), idx + 100000)):
            c = text[i]
            if escape: escape = False; continue
            if c == '\\' and in_str: escape = True; continue
            if c == '"': in_str = not in_str; continue
            if in_str: continue
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0: end_pos = i + 1; break
        
        if end_pos > idx + 50:
            snippet = text[idx:end_pos]
            # Quick check: does it contain any of the keywords?
            if any(kw in snippet for kw in keywords):
                try:
                    obj = json.loads(snippet)
                    if isinstance(obj, dict):
                        key = str(sorted(obj.items())[:3])
                        if key not in seen:
                            seen.add(key)
                            objects.append(obj)
                except Exception:
                    pass
            pos = end_pos
        else:
            pos = idx + 1
    
    print(f"  Found {len(objects)} unique {label} objects")
    return objects

# Extract events
events = extract_json_objects(
    "region_events.bin",
    ['eventName', 'teamAName', 'visible', 'isHot'],
    "events"
)

if events:
    events.sort(key=lambda e: (e.get('priority', 99), e.get('category', ''), e.get('eventName', '')))
    out = os.path.join(OUT_DIR, "events.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved events.json ({len(events)} events)")
    # Preview
    for e in events[:3]:
        print(f"    - {e.get('eventName','?')} [{e.get('category','?')}] visible={e.get('visible','?')}")

# Extract event_cats and categories from the big cats region
event_cats = extract_json_objects(
    "region_cats.bin",
    ['categoryLogo', 'catId', 'categoryId'],
    "event_cats"
)

categories = extract_json_objects(
    "region_cats.bin",
    ['id', 'name'],
    "categories-candidates"
)

if event_cats:
    out = os.path.join(OUT_DIR, "event_cats.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(event_cats, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved event_cats.json ({len(event_cats)} categories)")
    for c in event_cats[:3]:
        print(f"    - {c}")

# Save small pure categories separately
pure_cats = [c for c in categories if len(c) <= 4 and 'id' in c and 'name' in c]
if pure_cats:
    out = os.path.join(OUT_DIR, "categories.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(pure_cats, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved categories.json ({len(pure_cats)} categories)")
    for c in pure_cats[:5]:
        print(f"    - {c}")

print("\n=== Summary of decrypted_output/ ===")
for fname in sorted(os.listdir(OUT_DIR)):
    fp = os.path.join(OUT_DIR, fname)
    print(f"  {fname}: {os.path.getsize(fp):,} bytes")
