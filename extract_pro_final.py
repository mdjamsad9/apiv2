import sys, json, os

sys.stdout.reconfigure(encoding='utf-8')
OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

DUMP = "dump_pro_final.bin"
print(f"Opening {DUMP}...")

with open(DUMP, "rb") as f:
    data = f.read()

print(f"Size: {len(data):,}")

# Find all occurrences of key JSON fields
targets = {
    b'"eventName"': "events",
    b'"categoryLogo"': "event_cats", 
    b'"visible"': "events",
}

print("\nFinding all matches...")
matches = {}
for pattern, typ in targets.items():
    pos = 0
    while True:
        idx = data.find(pattern, pos)
        if idx == -1:
            break
        matches[idx] = (typ, pattern)
        pos = idx + 1

print(f"Total matches: {len(matches)}")

# Group into clusters
sorted_offsets = sorted(matches.keys())
clusters = []
current_cluster = [sorted_offsets[0]] if sorted_offsets else []

for off in sorted_offsets[1:]:
    if off - current_cluster[-1] < 200000:
        current_cluster.append(off)
    else:
        clusters.append(current_cluster)
        current_cluster = [off]
if current_cluster:
    clusters.append(current_cluster)

print(f"\nClusters ({len(clusters)}):")
for c in clusters:
    print(f"  [{c[0]:,} - {c[-1]:,}] {len(c)} matches, types: {set(matches[o][0] for o in c)}")

# Extract from each cluster
all_objects = {}

def extract_objects(chunk_bytes):
    text = chunk_bytes.decode('utf-8', errors='replace')
    objects = []
    seen = set()
    pos = 0
    
    while True:
        idx = text.find('{"', pos)
        if idx == -1:
            break
        
        depth = 0; in_str = False; escape = False; end_pos = -1
        for i in range(idx, min(len(text), idx + 200000)):
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
            try:
                obj = json.loads(snippet)
                if isinstance(obj, dict) and len(obj) > 2:
                    key = json.dumps({k: str(v)[:30] for k, v in sorted(obj.items())[:4]})
                    if key not in seen:
                        seen.add(key)
                        objects.append(obj)
            except Exception:
                pass
            pos = end_pos
        else:
            pos = idx + 1
    
    return objects

events = []
event_cats = []

for i, cluster in enumerate(clusters):
    start = max(0, cluster[0] - 5000)
    end = min(len(data), cluster[-1] + 50000)
    chunk = data[start:end]
    
    cluster_types = set(matches[o][0] for o in cluster)
    print(f"\nProcessing cluster {i+1}: {start:,}-{end:,}, types={cluster_types}")
    
    objs = extract_objects(chunk)
    print(f"  Extracted {len(objs)} objects")
    
    for obj in objs:
        keys = set(obj.keys())
        if 'eventName' in keys or 'visible' in keys or 'teamAName' in keys:
            events.append(obj)
        elif 'categoryLogo' in keys:
            event_cats.append(obj)
    
    print(f"  Events so far: {len(events)}, Cats so far: {len(event_cats)}")

# Deduplicate
def dedup(lst, key_fields):
    seen = set()
    result = []
    for obj in lst:
        key = tuple(str(obj.get(f, '')) for f in key_fields)
        if key not in seen:
            seen.add(key)
            result.append(obj)
    return result

events = dedup(events, ['eventName', 'category', 'teamAName'])
event_cats = dedup(event_cats, ['categoryLogo', 'catId'])

print(f"\n=== RESULTS ===")
print(f"Events: {len(events)}")
print(f"Event cats: {len(event_cats)}")

if events:
    events.sort(key=lambda e: (e.get('priority', 99), e.get('category', '')))
    with open(os.path.join(OUT_DIR, "events.json"), 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved events.json ({len(events)} events)")
    for e in events[:5]:
        print(f"  - [{e.get('category','?')}] {e.get('eventName','?')} visible={e.get('visible','?')}")

if event_cats:
    with open(os.path.join(OUT_DIR, "event_cats.json"), 'w', encoding='utf-8') as f:
        json.dump(event_cats, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved event_cats.json ({len(event_cats)} cats)")

# Also look at the first cluster for categories.json data
if clusters:
    start = max(0, clusters[0][0] - 100000)
    end = min(len(data), clusters[0][0] + 200000)
    chunk = data[start:end]
    text = chunk.decode('utf-8', errors='replace')
    # Find arrays
    for arr_start in range(0, len(text) - 1):
        if text[arr_start] == '[' and text[arr_start+1] == '{':
            depth = 0; in_str = False; escape = False; end_pos = -1
            for i in range(arr_start, min(len(text), arr_start + 1000000)):
                c = text[i]
                if escape: escape = False; continue
                if c == '\\' and in_str: escape = True; continue
                if c == '"': in_str = not in_str; continue
                if in_str: continue
                if c == '[': depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0: end_pos = i + 1; break
            if end_pos > arr_start + 500:
                snippet = text[arr_start:end_pos]
                try:
                    arr = json.loads(snippet)
                    if isinstance(arr, list) and len(arr) > 3:
                        print(f"\nFound JSON array at local offset {arr_start}: {len(arr)} items")
                        print(f"  First: {str(arr[0])[:200]}")
                        fname = f"arr_{clusters[0][0]+arr_start}.json"
                        with open(os.path.join(OUT_DIR, fname), 'w', encoding='utf-8') as f:
                            json.dump(arr, f, indent=2, ensure_ascii=False)
                        print(f"  Saved as {fname}")
                except Exception:
                    pass
