from pathlib import Path
from Decode.base_decoder import decode_data
from Hashing.hash_utils import hash_data

lines = Path("0nLy0ne.txt").read_text().splitlines()
for line in lines[1:]:
    uid, app, cred, stored = decode_data(line, "Base64").split("|")
    expected = hash_data(f"{uid}|{app}|{cred}", "sha256")[:8]
    if stored != expected:
        print(uid, app, cred, stored, expected)