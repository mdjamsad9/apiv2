"""
live_dump_search.py
Dump the running Crexify TV process heap and search for decrypted JSON.
"""
import subprocess, sys, json, os, time

sys.stdout.reconfigure(encoding='utf-8')
OUT_DIR = "decrypted_output"
os.makedirs(OUT_DIR, exist_ok=True)

def run(cmd, timeout=30):
    r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
    return r.stdout, r.stderr

# Get PID of crexify
print("Getting Crexify TV PID...")
out, _ = run("adb shell su -c \"ps -A | grep crexify | awk '{print $2}'\"")
pid = out.decode().strip().split('\n')[0]
if not pid.isdigit():
    # Relaunch
    print("App not running, launching...")
    run("adb shell monkey -p com.crexify.tv -c android.intent.category.LAUNCHER 1")
    time.sleep(8)
    out, _ = run("adb shell su -c \"ps -A | grep crexify | awk '{print $2}'\"")
    pid = out.decode().strip().split('\n')[0]

print(f"PID: {pid}")

# Read /proc/<pid>/maps to find heap regions
print("Reading memory maps...")
out, _ = run(f"adb shell su -c \"cat /proc/{pid}/maps | grep -E '(heap|anon:dalvik-main)' | head -20\"")
maps_str = out.decode('utf-8', errors='replace').strip()
print("Memory maps:")
print(maps_str)

# Parse heap regions
regions = []
for line in maps_str.split('\n'):
    if not line.strip():
        continue
    parts = line.split()
    if not parts:
        continue
    addr_range = parts[0]
    if '-' not in addr_range:
        continue
    start_hex, end_hex = addr_range.split('-')
    try:
        start = int(start_hex, 16)
        end = int(end_hex, 16)
        size = end - start
        # Only include regions with r permissions and reasonable size
        perms = parts[1] if len(parts) > 1 else ''
        if 'r' in perms and size > 65536 and size < 200_000_000:
            regions.append((start, end, size, perms))
    except Exception:
        pass

print(f"\nFound {len(regions)} readable memory regions")

all_events = []
all_cats = []

def extract_objects_from_bytes(data, keywords):
    text = data.decode('utf-8', errors='replace')
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
            if any(kw in snippet for kw in keywords) and len(snippet) > 100:
                try:
                    obj = json.loads(snippet)
                    if isinstance(obj, dict):
                        key = json.dumps(sorted(obj.items())[:3], ensure_ascii=False)
                        if key not in seen:
                            seen.add(key)
                            objects.append(obj)
                except Exception:
                    pass
            pos = end_pos
        else:
            pos = idx + 1
    
    return objects

# Process each region
for i, (start, end, size, perms) in enumerate(regions[:20]):
    hex_start = hex(start)
    print(f"\n[{i+1}/{min(len(regions), 20)}] Region {hex_start}, size {size:,} bytes, perms={perms}")
    
    # Use dd to read from /proc/<pid>/mem at the absolute offset
    cmd = f"adb shell su -c \"dd if=/proc/{pid}/mem bs=4096 skip={start // 4096} count={size // 4096 + 1} 2>/dev/null | strings | grep -E '(eventName|categoryLogo|teamAName)' | head -3\""
    out, _ = run(cmd, timeout=20)
    if out.strip():
        print(f"  HIT! Found JSON strings: {out.decode('utf-8', errors='replace').strip()[:200]}")

print("\nDone with live dump search.")
