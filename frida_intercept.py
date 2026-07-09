"""
frida_intercept.py - Start frida-server, hook Crexify TV, capture decrypted JSON.
Usage: python frida_intercept.py
"""
import subprocess
import threading
import time
import sys
import os
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

PACKAGE = "com.crexify.tv"
FRIDA_SERVER_PATH = "/data/local/tmp/frida-server"
HOOK_SCRIPT = os.path.join(os.path.dirname(__file__), "frida_hook.js")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "decrypted_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Step 1: Kill any existing frida-server ──────────────────────────────────
print("[1] Killing any existing frida-server...")
subprocess.run(["adb", "shell", "su", "-c", "pkill -f frida-server"], capture_output=True)
time.sleep(1)

# ── Step 2: Launch frida-server on emulator ─────────────────────────────────
print("[2] Starting frida-server on emulator...")
srv = subprocess.Popen(
    ["adb", "shell", "su", "-c", f"{FRIDA_SERVER_PATH} &"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(3)

# ── Step 3: Force-stop and relaunch the Crexify app ────────────────────────
print("[3] Force-stopping Crexify TV...")
subprocess.run(["adb", "shell", "am", "force-stop", PACKAGE], capture_output=True)
time.sleep(1)

# ── Step 4: Read hook script ────────────────────────────────────────────────
print("[4] Reading Frida hook script...")
with open(HOOK_SCRIPT, "r", encoding="utf-8") as f:
    jscode = f.read()

# ── Step 5: Launch Frida ────────────────────────────────────────────────────
print(f"[5] Attaching Frida to {PACKAGE} (spawn mode)...")
print("    Captured JSON outputs will be saved to decrypted_output/\n")

captured_jsons = []
output_lines = []

try:
    import frida

    def on_message(message, data):
        if message["type"] == "send":
            payload = message["payload"]
            print("[FRIDA]", payload)
            output_lines.append(payload)
            # Try to extract JSON from output
            json_match = re.search(r'(\[.*\]|\{.*\})', payload, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    captured_jsons.append(parsed)
                    fname = f"capture_{len(captured_jsons)}.json"
                    with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
                        json.dump(parsed, f, indent=2, ensure_ascii=False)
                    print(f"[+] Saved {fname}")
                except Exception:
                    pass
        elif message["type"] == "error":
            print(f"[FRIDA ERROR] {message['description']}")

    device = frida.get_usb_device()
    pid = device.spawn([PACKAGE])
    session = device.attach(pid)
    script = session.create_script(jscode)
    script.on("message", on_message)
    script.load()
    device.resume(pid)

    print("[*] App launched with Frida hooks. Waiting 30 seconds for network calls...")
    print("    (Use the app now - navigate to Events/Channels to trigger decryption)\n")
    time.sleep(30)

    print(f"\n[*] Captured {len(captured_jsons)} JSON responses.")
    print("[*] All output:")
    for line in output_lines:
        print(" ", line)

    script.unload()
    session.detach()

except Exception as e:
    print(f"[ERROR] Frida failed: {e}")
    print("\nFalling back to frida CLI mode:")
    print(f"  Run manually: frida -U -f {PACKAGE} -l frida_hook.js --no-pause")

print("\n[Done] Check decrypted_output/ for captured JSON files.")
