import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

offset = 11350000 - 500000  # Start 500KB earlier to make sure we cover it
count = 1000000  # Read 1MB of memory

cmd = f'adb shell su -c "dd if=/data/local/tmp/dump_new.bin bs=1 skip={offset} count={count}"'
print(f"Streaming {count} bytes from offset {offset}...")

process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

if process.returncode != 0:
    print("Error:", stderr.decode('utf-8', errors='ignore'))
    sys.exit(1)

# Try decoding as UTF-16 LE
print("Decoding as UTF-16 LE...")
text_u16 = stdout.decode('utf-16-le', errors='ignore')

# Try finding categoryLogo or other JSON indicators in UTF-16
print("Searching in UTF-16 string...")
idx = 0
while True:
    idx = text_u16.find('categoryLogo', idx)
    if idx == -1:
        break
    print(f"\nFound 'categoryLogo' at index {idx} in UTF-16 block:")
    start = max(0, idx - 200)
    end = min(len(text_u16), idx + 2000)
    print("-" * 80)
    print(repr(text_u16[start:end]))
    print("-" * 80)
    idx += 12

# Also check UTF-8
print("\nDecoding as UTF-8...")
text_u8 = stdout.decode('utf-8', errors='ignore')
idx = 0
while True:
    idx = text_u8.find('categoryLogo', idx)
    if idx == -1:
        break
    print(f"\nFound 'categoryLogo' at index {idx} in UTF-8 block:")
    start = max(0, idx - 200)
    end = min(len(text_u8), idx + 2000)
    print("-" * 80)
    print(repr(text_u8[start:end]))
    print("-" * 80)
    idx += 12
