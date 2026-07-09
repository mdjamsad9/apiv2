import urllib.request
import base64
import json
import os
import sys
import binascii
from Crypto.Cipher import AES

sys.stdout.reconfigure(encoding="utf-8")

# Load Config
config_path = "app_control.json"
if not os.path.exists(config_path):
    print("Error: app_control.json not found.")
    sys.exit(1)

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

active_source = config.get("active_source", "crexify")
profile = config["sources"][active_source]

# Active profile parameters
genz_url = profile["genz_url"]
token = profile["token"]
aes_key_bytes = profile["aes_key"].encode('utf-8')
aes_iv_bytes = profile["aes_iv"].encode('utf-8')
xor_key_val = profile["xor_key"]
keys_paths_encrypted = profile["keys"]

# Set up output directories
out_dir = "decrypted_output"
os.makedirs(out_dir, exist_ok=True)
pro_dir = os.path.join(out_dir, "pro")
os.makedirs(pro_dir, exist_ok=True)
ch_dir = os.path.join(out_dir, "channels")
os.makedirs(ch_dir, exist_ok=True)

github_user = os.environ.get("GITHUB_REPOSITORY_OWNER", "mdjamsad9")
github_repo = os.environ.get("GITHUB_REPOSITORY", "mdjamsad9/apiv2").split("/")[-1]
pages_base = f"https://{github_user}.github.io/{github_repo}/decrypted_output"

print(f"Active Profile: {active_source}")
print(f"Genz Config URL: {genz_url}")
print(f"Pages Base URL: {pages_base}")

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────

def make_request(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        print(f"  Request failed for {url}: {e}")
        return None

def cfgMaterial():
    bArr = [29, 88, 17, 104, 66, 7, 91, 34, 113, 5, 47, 96]
    bArr2 = [71, 12, 83, 44, 9, 121, 36, 58, 101, 22, 63]
    bArr3 = [6, 39, 95, 14, 74, 52, 117, 27, 68, 3, 86, 41, 109]
    bArr4 = bytearray(32)
    for i in range(32):
        i10 = bArr[i % 12] & 255
        i11 = bArr2[((i * 3) + 1) % 11] & 255
        i12 = i & 7
        
        shift_r = 8 - i12
        term1 = (i11 & 0xffffffff) >> shift_r
        term2 = (i11 << i12) & 0xffffffff
        rotated = (term1 | term2) & 255
        
        val = (((i10 ^ rotated) ^ (bArr3[((i * 5) + 2) % 13] & 255)) ^ 90) ^ i
        bArr4[i] = val & 255
    return bArr4

def decrypt_cfj1(str_val):
    str_val = str_val.strip()
    if str_val.startswith("cfj1:"):
        str_val = str_val[5:]
    
    str_val = str_val.replace("\r", "").replace("\n", "").replace("\t", "").replace(" ", "")
    bArrDecode = base64.b64decode(str_val)
    bArrCfgMaterial = cfgMaterial()
    bArr = bytearray(len(bArrDecode))
    
    for i in range(len(bArrDecode)):
        val = (((bArrCfgMaterial[i % len(bArrCfgMaterial)] & 255) ^ bArrDecode[i]) ^ (((i * 29) + 71) & 255)) & 255
        bArr[len(bArrDecode) - 1 - i] = val
        
    return bArr.decode('utf-8', errors='ignore')

def decrypt_xor_hex(hex_str):
    try:
        data = binascii.unhexlify(hex_str)
        decrypted = bytes([b ^ xor_key_val for b in data])
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"XOR Decrypt Error: {e}")
        return None

def clean_base64(s):
    sb = []
    for c in s:
        if ('A' <= c <= 'Z') or ('a' <= c <= 'z') or ('0' <= c <= '9') or c == '+' or c == '/':
            sb.append(c)
    s_cleaned = "".join(sb)
    while len(s_cleaned) % 4 != 0:
        s_cleaned += '='
    return s_cleaned

def decrypt_aes_v2(raw_bytes, suffix_len=16):
    if not raw_bytes:
        return None
    try:
        # Layer 1 Base64 Decode
        data1 = base64.b64decode(raw_bytes.strip())
        data1_str = data1.decode('utf-8', errors='ignore')
        
        # Swap Pairs
        swapped = list(data1_str)
        for i in range(0, len(swapped)-1, 2):
            swapped[i], swapped[i+1] = swapped[i+1], swapped[i]
            
        # Reverse Chars
        rev = swapped[::-1]
        rev_str = "".join(rev)
        
        # Strip Suffix
        if suffix_len > 0:
            rev_str = rev_str[:-suffix_len]
            
        # Layer 2 Base64 Decode
        cleaned = clean_base64(rev_str)
        data2 = base64.b64decode(cleaned)
        
        # AES Decrypt
        cipher = AES.new(aes_key_bytes, AES.MODE_CBC, aes_iv_bytes)
        dec = cipher.decrypt(data2[:(len(data2)//16)*16])
        
        # Strip PKCS7 Padding
        pad_len = dec[-1]
        if 1 <= pad_len <= 16 and all(x == pad_len for x in dec[-pad_len:]):
            plain = dec[:-pad_len]
        else:
            plain = dec
        plain_str = plain.decode('utf-8', errors='ignore')
        
        # Layer 3 Swap & Reverse
        swapped2 = list(plain_str)
        for i in range(0, len(swapped2)-1, 2):
            swapped2[i], swapped2[i+1] = swapped2[i+1], swapped2[i]
        rev2 = swapped2[::-1]
        
        # Layer 4 Final Base64 Decode
        cleaned2 = clean_base64("".join(rev2))
        final = base64.b64decode(cleaned2)
        return final
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None

def save_output(filename, data_str_or_bytes, custom_dir=None):
    target_dir = custom_dir if custom_dir else out_dir
    base_name = filename.rsplit('.', 1)[0]
    
    json_path = os.path.join(target_dir, f"{base_name}.json")
    txt_path = os.path.join(target_dir, f"{base_name}.txt")
    
    is_bytes = isinstance(data_str_or_bytes, bytes)
    
    # Write json file
    if is_bytes:
        try:
            parsed = json.loads(data_str_or_bytes.decode('utf-8', errors='ignore'))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
        except Exception:
            with open(json_path, "wb") as f:
                f.write(data_str_or_bytes)
    else:
        try:
            parsed = json.loads(data_str_or_bytes)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
        except Exception:
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(data_str_or_bytes)
                
    # Write txt file (exact same content)
    if is_bytes:
        with open(txt_path, "wb") as f:
            f.write(data_str_or_bytes)
    else:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(data_str_or_bytes)

# ─── PIPELINE EXECUTION ──────────────────────────────────────────────────────

raw_pro_links = []
custom_channels_to_fetch = []

# Step 1: Fetch and decrypt genz config
print("\n=== Fetching dynamic genz config ===")
genz_raw = make_request(genz_url)
if not genz_raw:
    print("Error: Could not retrieve dynamic config.")
    sys.exit(1)

genz_decrypted_str = decrypt_cfj1(genz_raw.decode('utf-8', errors='ignore'))
try:
    genz_config = json.loads(genz_decrypted_str)
    print("Dynamic Config successfully decrypted.")
    api_url = genz_config.get("api_url", genz_config.get("api2", ""))
    if not api_url:
        print("Error: api_url not found in decrypted dynamic config.")
        sys.exit(1)
    if not api_url.endswith('/'):
        api_url += '/'
    print(f"API Target Host: {api_url}")
except Exception as e:
    print(f"Error parsing dynamic config JSON: {e}")
    sys.exit(1)

# Modify and save app.json (using genz config)
genz_config["api_url"] = pages_base + "/"
genz_config["api2"] = pages_base + "/"
if "web_url" in genz_config:
    genz_config["web_url"] = pages_base + "/"
save_output("app.json", json.dumps([genz_config], indent=2, ensure_ascii=False))
print("✓ Saved app.json")

# Step 2: Fetch and decrypt event_cats.txt
event_cats_path = decrypt_xor_hex(keys_paths_encrypted["event_cats.json"])
print(f"\n=== Fetching event_cats: {event_cats_path} ===")
event_cats_raw = make_request(api_url + event_cats_path)
event_cats_decrypted = decrypt_aes_v2(event_cats_raw, suffix_len=16)
if event_cats_decrypted:
    save_output("event_cats.json", event_cats_decrypted)
    print("✓ Saved event_cats.json")
else:
    print("Error decrypting event_cats.txt")

# Step 3: Fetch and decrypt categories.txt
categories_path = decrypt_xor_hex(keys_paths_encrypted["categories.json"])
print(f"\n=== Fetching categories: {categories_path} ===")
categories_raw = make_request(api_url + categories_path)
categories_decrypted = decrypt_aes_v2(categories_raw, suffix_len=16)

if categories_decrypted:
    try:
        cats_list = json.loads(categories_decrypted.decode('utf-8', errors='ignore'))
        
        # Rewrite custom channel URLs and extract their filenames
        for item in cats_list:
            if isinstance(item, dict):
                # Check for "cat" nested JSON object
                if "cat" in item:
                    cat_data = json.loads(item["cat"])
                    if isinstance(cat_data, dict):
                        api_val = cat_data.get("api", "")
                        if api_val and api_val.startswith("channels/"):
                            filename = api_val.split("channels/")[-1]
                            custom_channels_to_fetch.append(filename)
                            # Rewrite
                            cat_data["api"] = f"{pages_base}/{api_val}"
                            item["cat"] = json.dumps(cat_data, ensure_ascii=False)
        
        # Hardcode the Sports tab navigation channel file U3BvcnRzMTc2OTQ0MDUwMjE4Ng.txt
        custom_channels_to_fetch.append("U3BvcnRzMTc2OTQ0MDUwMjE4Ng.txt")
        
        categories_modified_str = json.dumps(cats_list, indent=2, ensure_ascii=False)
        save_output("categories.json", categories_modified_str)
        print(f"✓ Saved categories.json")
    except Exception as e:
        print(f"Error parsing categories JSON: {e}")
else:
    print("Error decrypting categories.txt")

# Step 4: Fetch and decrypt events.txt
events_path = decrypt_xor_hex(keys_paths_encrypted["events.json"])
print(f"\n=== Fetching events: {events_path} ===")
events_raw = make_request(api_url + events_path)
events_decrypted = decrypt_aes_v2(events_raw, suffix_len=16)

if events_decrypted:
    try:
        events_outer_list = json.loads(events_decrypted.decode('utf-8', errors='ignore'))
        
        # Rewrite links and gather raw original pro links
        for item in events_outer_list:
            if isinstance(item, dict) and "event" in item:
                ev_data = json.loads(item["event"])
                if isinstance(ev_data, dict):
                    lnk = ev_data.get("links", "")
                    if lnk and lnk.startswith("pro/"):
                        raw_pro_links.append(lnk)
                        ev_data["links"] = f"{pages_base}/{lnk}"
                    item["event"] = json.dumps(ev_data, ensure_ascii=False)
                    
        events_modified_str = json.dumps(events_outer_list, indent=2, ensure_ascii=False)
        save_output("events.json", events_modified_str)
        print(f"✓ Saved events.json ({len(events_outer_list)} events found)")
    except Exception as e:
        print(f"Error parsing events JSON: {e}")
else:
    print("Error decrypting events.txt")

# Step 5: Download and decrypt dynamic channels/ files
print(f"\n=== Fetching dynamic channels/ files ({len(custom_channels_to_fetch)} custom channels) ===")
ch_saved = 0

for filename in custom_channels_to_fetch:
    if not filename:
        continue
    
    # Map hardcoded CrexiFy tab channels/U3BvcnRzMTc2OTQ0MDUwMjE4Ng.txt 
    # to original Cricfy server channels/U3BvcnRzIEhvbWUgUHJvMTc2OTQ0MTM3ODY0MA.txt
    original_filename = filename
    if filename == "U3BvcnRzMTc2OTQ0MDUwMjE4Ng.txt":
        original_filename = "U3BvcnRzIEhvbWUgUHJvMTc2OTQ0MTM3ODY0MA.txt"
        
    ch_raw = make_request(f"{api_url}v2/channels/{original_filename}")
    if ch_raw:
        ch_decrypted = decrypt_aes_v2(ch_raw, suffix_len=16)
        if ch_decrypted:
            try:
                ch_list = json.loads(ch_decrypted.decode('utf-8', errors='ignore'))
                # For each channel, find if it has nested JSON to rewrite pro links
                for item in ch_list:
                    if isinstance(item, dict) and "channel" in item:
                        ch_data = json.loads(item["channel"])
                        if isinstance(ch_data, dict):
                            lnk = ch_data.get("links", "")
                            if lnk and lnk.startswith("pro/"):
                                raw_pro_links.append(lnk)
                                ch_data["links"] = f"{pages_base}/{lnk}"
                            item["channel"] = json.dumps(ch_data, ensure_ascii=False)
                
                ch_modified_str = json.dumps(ch_list, indent=2, ensure_ascii=False)
                save_output(filename, ch_modified_str, custom_dir=ch_dir)
                ch_saved += 1
            except Exception as e:
                # If JSON parsing failed, save the raw decrypted data
                save_output(filename, ch_decrypted, custom_dir=ch_dir)
                ch_saved += 1
        else:
            print(f"  Failed decrypting channels/{original_filename}")
            # Save empty array to prevent 404 error on user's Pages
            save_output(filename, b"[]", custom_dir=ch_dir)
    else:
        print(f"  Failed fetching channels/{original_filename}")
        # Save empty array to prevent 404 error on user's Pages
        save_output(filename, b"[]", custom_dir=ch_dir)

print(f"✓ Saved {ch_saved} channel files")

# Step 6: Download and decrypt dynamic pro/ stream files
# Remove duplicates from raw_pro_links to avoid redundant network requests
raw_pro_links = list(set(raw_pro_links))
print(f"\n=== Fetching dynamic pro/ files ({len(raw_pro_links)} unique streams) ===")
pro_saved = 0

for lnk in raw_pro_links:
    filename = lnk.split("pro/")[-1]
    if not filename:
        continue
    
    pro_raw = make_request(f"{api_url}v2/pro/{filename}")
    if pro_raw:
        pro_decrypted = decrypt_aes_v2(pro_raw, suffix_len=16)
        if pro_decrypted:
            save_output(filename, pro_decrypted, custom_dir=pro_dir)
            pro_saved += 1
        else:
            print(f"  Failed decrypting pro/{filename}")
    else:
        print(f"  Failed fetching pro/{filename}")

print(f"✓ Saved {pro_saved} pro files")

# Step 7: Generate gateway.json dynamically
print("\n=== Generating gateway.json ===")
gateway_data = {
    "service": "CrexiFy TV Decrypted API Gateway",
    "base_url": pages_base + "/",
    "endpoints": {
        "startup_config": {
            "url": f"{pages_base}/app.json",
            "description": "Global app configuration, popups, and api redirection urls."
        },
        "categories": {
            "url": f"{pages_base}/categories.json",
            "description": "Main channel category list containing category names, logos, types, and 'table_name'."
        },
        "channels": {
            "url_pattern": f"{pages_base}/channels/{{table_name}}.json",
            "sports_tab_url": f"{pages_base}/channels/U3BvcnRzMTc2OTQ0MDUwMjE4Ng.json",
            "description": "Decrypted direct streaming URLs, DRM decryption keys, names, and logos for a specific category table_name."
        },
        "live_matches": {
            "url": f"{pages_base}/events.json",
            "description": "List of active live matches (cricket, football, etc.) with stream URLs and DRM keys."
        },
        "sports_logos": {
            "url": f"{pages_base}/event_cats.json",
            "description": "Key-value dictionary mapping tournament names to logo URLs."
        }
    }
}

try:
    with open("gateway.json", "w", encoding="utf-8") as f:
        json.dump(gateway_data, f, indent=2, ensure_ascii=False)
    print("✓ Saved gateway.json at the root")
except Exception as e:
    print(f"Failed to save gateway.json: {e}")

print("\n==================================================")
print(f"SUMMARY: 4/4 main files, {ch_saved} channels, {pro_saved} pro stream files decrypted.")
print("Done!")

