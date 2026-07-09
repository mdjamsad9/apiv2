"""
reverse_engineer.py
We have:
  - A known plaintext (events.json from memory dump)
  - The encrypted events.txt from the server

Use this to figure out the exact decryption pipeline.
"""
import urllib.request, base64, sys, json, os
from Crypto.Cipher import AES

sys.stdout.reconfigure(encoding='utf-8')

# Load known decrypted events from memory
with open("decrypted_output/events.json", 'r', encoding='utf-8') as f:
    known_events = json.load(f)

# Get first event's unique data for verification
target_str = known_events[0].get('eventName', '')
print(f"Will search for target string: '{target_str}'")

# Fetch the encrypted events.txt
print("Fetching events.txt from server...")
req = urllib.request.Request('https://crex-api.pages.dev/events.txt', 
                             headers={'User-Agent': 'Mozilla/5.0'})
raw = urllib.request.urlopen(req, timeout=15).read().decode('utf-8').strip()
print(f"Raw events.txt length: {len(raw)}")
print(f"First 100 chars: {raw[:100]}")
print(f"Last 50 chars: {raw[-50:]}")

# ─── Decryption helpers ────────────────────────────────────────────────────
def swap_pairs(s):
    arr = list(s)
    for i in range(0, len(arr)-1, 2):
        arr[i], arr[i+1] = arr[i+1], arr[i]
    return ''.join(arr)

def clean_b64(s, strip_eq=True):
    valid = ''.join(c for c in s if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/')
    if not strip_eq:
        valid = valid + '=' * ((4 - len(valid) % 4) % 4)
    return valid

def try_b64(s):
    try:
        cleaned = clean_b64(s, strip_eq=False)
        return base64.b64decode(cleaned)
    except Exception as e:
        return None

def try_aes(ciphertext, key, iv):
    try:
        if len(ciphertext) % 16 != 0:
            return None
        cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
        dec = cipher.decrypt(ciphertext)
        # Remove PKCS7 padding
        pad = dec[-1]
        if 1 <= pad <= 16 and all(x == pad for x in dec[-pad:]):
            dec = dec[:-pad]
        return dec
    except Exception:
        return None

keys = {
    'SetA': ('l2K5wB8xC1wP7rK1', 'n0K4nP8uB8hH1l18'),
    'SetB': ('k8Ml5bk4xK1kM9oP', 'G6K4nM8mVlBL8p51'),
}

def check(result, label):
    if result and isinstance(result, (bytes, str)):
        if isinstance(result, bytes):
            try:
                s = result.decode('utf-8', errors='ignore')
            except Exception:
                return False
        else:
            s = result
        if target_str in s or s.strip().startswith('[') or s.strip().startswith('{'):
            print(f"\n✓✓✓ PIPELINE FOUND: {label}")
            print(f"    Preview: {s[:300]}")
            return True
    return False

print("\n─── Testing decryption pipelines ───\n")

# Stage 1 variations of raw input
stage1 = {
    'raw': raw,
    'raw_stripped': raw.rstrip('='),
    'raw_rev': raw[::-1],
    'raw_swap': swap_pairs(raw),
    'raw_swap_rev': swap_pairs(raw)[::-1],
    'raw_rev_swap': swap_pairs(raw[::-1]),
}

for s1_name, s1_val in stage1.items():
    b1 = try_b64(s1_val)
    if b1 is None:
        continue
    
    # Try direct AES on b1
    for kname, (key, iv) in keys.items():
        result = try_aes(b1, key, iv)
        if check(result, f"{s1_name} → b64 → AES({kname})"):
            continue
    
    # Try decoding b1 as UTF-8 string and transforming
    try:
        s2 = b1.decode('utf-8', errors='ignore')
    except Exception:
        continue
    
    s2_variants = {
        's2': s2,
        's2_rev': s2[::-1],
        's2_swap': swap_pairs(s2),
        's2_swap_rev': swap_pairs(s2)[::-1],
        's2_rev_swap': swap_pairs(s2[::-1]),
    }
    
    for s2_name, s2_val in s2_variants.items():
        # Direct as ciphertext
        b2 = s2_val.encode('utf-8', errors='ignore')
        for kname, (key, iv) in keys.items():
            result = try_aes(b2, key, iv)
            if check(result, f"{s1_name} → b64 → {s2_name} → AES({kname})"):
                pass
        
        # Base64 decode s2_val then AES
        b2 = try_b64(s2_val)
        if b2 is None:
            continue
        
        for kname, (key, iv) in keys.items():
            result = try_aes(b2, key, iv)
            if check(result, f"{s1_name} → b64 → {s2_name} → b64 → AES({kname})"):
                # Now do post-process
                if result:
                    try:
                        s3 = result.decode('utf-8', errors='ignore')
                        for s3_name, s3_val in [
                            ('direct', s3), 
                            ('rev', s3[::-1]),
                            ('swap', swap_pairs(s3)),
                            ('swap_rev', swap_pairs(s3)[::-1]),
                            ('rev_swap', swap_pairs(s3[::-1]))
                        ]:
                            b3 = try_b64(s3_val)
                            if b3:
                                final = b3.decode('utf-8', errors='ignore')
                                if check(final, f"{s1_name}→b64→{s2_name}→b64→AES({kname})→{s3_name}→b64"):
                                    pass
                    except Exception:
                        pass

print("\nSearch complete.")
