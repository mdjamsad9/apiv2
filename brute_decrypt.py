import base64
import sys
from Crypto.Cipher import AES

sys.stdout.reconfigure(encoding='utf-8')

def swap_pairs(chars):
    arr = list(chars)
    for i in range(0, len(arr) - 1, 2):
        arr[i], arr[i+1] = arr[i+1], arr[i]
    return "".join(arr)

def reverse_chars(s):
    return s[::-1]

def clean_base64(s):
    sb = []
    for c in s:
        if ('A' <= c <= 'Z') or ('a' <= c <= 'z') or ('0' <= c <= '9') or c in '+/=':
            sb.append(c)
    s_cleaned = "".join(sb)
    # Ensure proper padding
    while len(s_cleaned) % 4 != 0:
        s_cleaned += '='
    return s_cleaned

keys = {
    'SetA': ('l2K5wB8xC1wP7rK1', 'n0K4nP8uB8hH1l18'),
    'SetB': ('k8Ml5bk4xK1kM9oP', 'G6K4nM8mVlBL8p51'),
    'Cricfy': ('WT1sdkEvUlR4ckd2', 'Q7sKcm9LR4VaX2pN')
}

with open('temp/event_cats.txt', 'r', encoding='utf-8') as f:
    raw_content = ''.join(f.read().split())

# Transformations of raw content before first base64 decode
raw_variants = {
    'direct': raw_content,
    'reversed': raw_content[::-1]
}

def is_valid_json_text(text):
    # Check if text looks like a valid JSON
    # It should start with { or [ and end with } or ] (allowing whitespace)
    t = text.strip()
    if not (t.startswith('{') or t.startswith('[')):
        return False
    # Check if it has a high proportion of printable characters (basic sanity check)
    printable = sum(1 for c in t if 32 <= ord(c) <= 126 or ord(c) in [10, 13, 9])
    if len(t) > 0 and (printable / len(t)) > 0.8:
        return True
    return False

print("Starting brute force decryption on event_cats.txt...")

for raw_name, raw_val in raw_variants.items():
    cleaned_raw = clean_base64(raw_val)
    try:
        b1 = base64.b64decode(cleaned_raw)
    except Exception:
        continue
    
    # Try decoding to string
    try:
        s1 = b1.decode('utf-8', errors='ignore')
    except Exception:
        continue
        
    s1_variants = {
        'none': s1,
        'rev': reverse_chars(s1),
        'swap': swap_pairs(s1),
        'swap_rev': reverse_chars(swap_pairs(s1)),
        'rev_swap': swap_pairs(reverse_chars(s1))
    }
    
    for s1_name, s1_val in s1_variants.items():
        # Option A: treat s1_val directly as ciphertext or base64 of ciphertext
        # 1. Direct ciphertext
        for kname, (key, iv) in keys.items():
            bArr = s1_val.encode('utf-8', errors='ignore')
            if len(bArr) > 0 and len(bArr) % 16 == 0:
                cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
                try:
                    dec = cipher.decrypt(bArr)
                    dec_str = dec.decode('utf-8', errors='ignore')
                    if is_valid_json_text(dec_str):
                        print(f"FOUND! Raw: {raw_name}, S1: {s1_name}, Type: DirectAES, Key: {kname}")
                        print("JSON Preview:", repr(dec_str[:200]))
                except Exception:
                    pass
                    
        # 2. Base64 encoded ciphertext
        cleaned_s1 = clean_base64(s1_val)
        try:
            b2 = base64.b64decode(cleaned_s1)
            if len(b2) > 0 and len(b2) % 16 == 0:
                for kname, (key, iv) in keys.items():
                    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
                    try:
                        dec = cipher.decrypt(b2)
                        # Decrypted plaintext can itself be base64 or swapped/reversed base64
                        dec_variants = {
                            'direct': dec.decode('utf-8', errors='ignore'),
                            'swap_rev': reverse_chars(swap_pairs(dec.decode('utf-8', errors='ignore'))),
                            'rev_swap': swap_pairs(reverse_chars(dec.decode('utf-8', errors='ignore')))
                        }
                        for dec_name, dec_str in dec_variants.items():
                            # Direct check
                            if is_valid_json_text(dec_str):
                                print(f"FOUND! Raw: {raw_name}, S1: {s1_name}, Type: B64-AES-{dec_name}, Key: {kname}")
                                print("JSON Preview:", repr(dec_str[:200]))
                            # Base64 check
                            try:
                                final_dec = base64.b64decode(clean_base64(dec_str)).decode('utf-8', errors='ignore')
                                if is_valid_json_text(final_dec):
                                    print(f"FOUND! Raw: {raw_name}, S1: {s1_name}, Type: B64-AES-{dec_name}-B64, Key: {kname}")
                                    print("JSON Preview:", repr(final_dec[:200]))
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass

print("Brute force search completed.")
