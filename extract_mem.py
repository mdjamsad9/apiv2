import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Run dd command to get memory block
offset = 11350000
count = 20000

cmd = f'adb shell su -c "dd if=/data/local/tmp/dump_new.bin bs=1 skip={offset} count={count}"'
print(f"Running: {cmd}")

process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

if process.returncode != 0:
    print("Error:", stderr.decode('utf-8', errors='ignore'))
    sys.exit(1)

# Extract printable strings from stdout bytes
strings = []
current = []
for b in stdout:
    if 32 <= b <= 126 or b in [10, 13, 9]:
        current.append(chr(b))
    else:
        if len(current) >= 4:
            strings.append("".join(current))
        current = []
if len(current) >= 4:
    strings.append("".join(current))

print(f"\nExtracted {len(strings)} strings:")
for s in strings:
    s_clean = s.strip()
    if 'categoryLogo' in s_clean or s_clean.startswith('[') or s_clean.startswith('{'):
        print("-" * 50)
        print(s_clean[:1000])
        print("-" * 50)
