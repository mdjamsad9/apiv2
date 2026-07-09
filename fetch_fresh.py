import urllib.request
import base64
import json
import os
import re
import sys
from Crypto.Cipher import AES

sys.stdout.reconfigure(encoding='utf-8')

# Load configuration
config_path = "app_control.json"
if not os.path.exists(config_path):
    print("Error: app_control.json not found.")
    sys.exit(1)

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

active_source = config.get("active_source", "crexify")
profile = config["sources"][active_source]

api_url = profile["api_url"]
keys = profile["keys"]

# Output directory
out_dir = "decrypted_output"
os.makedirs(out_dir, exist_ok=True)

# Helper functions for AES Decryption
def decrypt_aes(ciphertext, key, iv):
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec = cipher.decrypt(ciphertext)
        pad_len = dec[-1]
        if 1 <= pad_len <= 16:
            if all(x == pad_len for x in dec[-pad_len:]):
                dec = dec[:-pad_len]
        return dec
    except Exception as e:
        print("AES Decryption Error:", e)
        return None

def swap_pairs(chars):
    for i in range(0, len(chars) - 1, 2):
        chars[i], chars[i+1] = chars[i+1], chars[i]
    return chars

def reverse_chars(chars):
    return chars[::-1]

def preprocess_v2(content, suffix=""):
    try:
        b1 = base64.b64decode(content)
        s1 = b1.decode('utf-8', errors='ignore')
        s2 = "".join(reverse_chars(swap_pairs(list(s1))))
        if suffix:
            if not s2.endswith(suffix):
                return None
            s2 = s2[:-len(suffix)]
        
        # Keep only valid base64 chars
        sb = [c for c in s2 if ('A'<=c<='Z' or 'a'<=c<='z' or '0'<=c<='9' or c=='+' or c=='/')]
        s2_clean = "".join(sb)
        while len(s2_clean) % 4 != 0:
            s2_clean += '='
        return base64.b64decode(s2_clean)
    except Exception as e:
        print("V2 Preprocess Error:", e)
        return None

def make_request(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()

# 1. Decrypt app.txt (Direct Base64 -> AES CBC SetB)
print("Downloading app.txt...")
try:
    raw_app = make_request(f"{api_url}app.txt")
    cleaned_app = "".join(raw_app.decode('utf-8').strip().split())
    while len(cleaned_app) % 4 != 0:
        cleaned_app += "="
    ct_app = base64.b64decode(cleaned_app)
    
    key_b = keys["Crexify_SetB"]["aes_key"].encode('utf-8')
    iv_b = keys["Crexify_SetB"]["aes_iv"].encode('utf-8')
    
    dec_app = decrypt_aes(ct_app, key_b, iv_b)
    if dec_app:
        app_json = json.loads(dec_app.decode('utf-8', errors='ignore'))
        
        # Inject dynamic pages URL for API Redirection
        github_user = os.environ.get("GITHUB_REPOSITORY_OWNER", "mdjamsad9")
        github_repo = os.environ.get("GITHUB_REPOSITORY", "mdjamsad9/api").split("/")[-1]
        base_pages_url = f"https://{github_user}.github.io/{github_repo}/decrypted_output/"
        
        app_json["api_url"] = base_pages_url
        app_json["new_api"] = base_pages_url
        app_json["web_url"] = base_pages_url
        
        with open(os.path.join(out_dir, "app.json"), "w", encoding="utf-8") as f:
            json.dump(app_json, f, indent=2, ensure_ascii=False)
        print("-> app.json decrypted successfully!")
except Exception as e:
    print("-> Failed app.json:", e)

# 2. Decrypt event_cats.txt (Double Base64 + Swap + Reverse -> AES CBC SetA)
print("\nDownloading event_cats.txt...")
try:
    raw_cats = make_request(f"{api_url}event_cats.txt")
    ct_cats = preprocess_v2(raw_cats.decode('utf-8').strip())
    
    key_a = keys["Crexify_SetA"]["aes_key"].encode('utf-8')
    iv_a = keys["Crexify_SetA"]["aes_iv"].encode('utf-8')
    
    dec_cats = decrypt_aes(ct_cats, key_a, iv_a)
    if dec_cats:
        cats_json = json.loads(dec_cats.decode('utf-8', errors='ignore'))
        with open(os.path.join(out_dir, "event_cats.json"), "w", encoding="utf-8") as f:
            json.dump(cats_json, f, indent=2, ensure_ascii=False)
        print("-> event_cats.json decrypted successfully!")
except Exception as e:
    print("-> Failed event_cats.json:", e)

# 3. Decrypt events.txt (Double Base64 + Swap + Reverse -> AES CBC SetA)
print("\nDownloading events.txt...")
events_list = []
try:
    raw_events = make_request(f"{api_url}events.txt")
    ct_events = preprocess_v2(raw_events.decode('utf-8').strip())
    
    key_a = keys["Crexify_SetA"]["aes_key"].encode('utf-8')
    iv_a = keys["Crexify_SetA"]["aes_iv"].encode('utf-8')
    
    dec_events = decrypt_aes(ct_events, key_a, iv_a)
    if dec_events:
        events_json = json.loads(dec_events.decode('utf-8', errors='ignore'))
        
        # Write clean events to output
        with open(os.path.join(out_dir, "events.json"), "w", encoding="utf-8") as f:
            json.dump(events_json, f, indent=2, ensure_ascii=False)
        print("-> events.json decrypted successfully!")
        
        events_list = events_json
except Exception as e:
    print("-> Failed events.json:", e)

# 4. Decrypt individual pro event stream files
pro_dir = os.path.join(out_dir, "pro")
os.makedirs(pro_dir, exist_ok=True)

print("\nProcessing pro event stream files...")
for idx, event in enumerate(events_list):
    pro_path = event.get("links") # e.g. pro/RklGQSBXb3JsZCBD...txt
    teamA = event.get("teamAName", "TeamA")
    teamB = event.get("teamBName", "TeamB")
    
    if pro_path and pro_path.startswith("pro/"):
        filename = pro_path.split("/")[-1]
        print(f"Decrypting stream links for {teamA} vs {teamB} ({filename})...")
        
        try:
            pro_url = f"{api_url}{pro_path}"
            raw_pro = make_request(pro_url)
            
            # Direct Base64 -> AES CBC SetB
            cleaned_pro = "".join(raw_pro.decode('utf-8').strip().split())
            while len(cleaned_pro) % 4 != 0:
                cleaned_pro += "="
            ct_pro = base64.b64decode(cleaned_pro)
            
            key_b = keys["Crexify_SetB"]["aes_key"].encode('utf-8')
            iv_b = keys["Crexify_SetB"]["aes_iv"].encode('utf-8')
            
            dec_pro = decrypt_aes(ct_pro, key_b, iv_b)
            if dec_pro:
                pro_text = dec_pro.decode('utf-8', errors='ignore')
                
                # Split entries (Format is name, url, keys/headers)
                # We can clean up the parsed output and format it as a JSON array
                entries = []
                lines = [line.strip() for line in pro_text.splitlines() if line.strip()]
                
                # The raw text contains: Name, URL, DRM Key, User-Agent in sequential blocks
                # We write the raw decrypted content directly as a json/text file
                with open(os.path.join(pro_dir, filename), "w", encoding="utf-8") as f:
                    f.write(pro_text)
                print(f"  -> Decrypted {filename} successfully!")
        except Exception as e:
            print(f"  -> Failed {filename}: {e}")

print("\nAll decryption processes completed successfully. Output files saved to:", os.path.abspath(out_dir))
