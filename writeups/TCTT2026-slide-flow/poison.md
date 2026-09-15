### Slide Flow

**The Poisoned Package**

---

#### ขั้น 1 — เจออะไรในไฟล์

เปิด `evidence.zip` ด้วย Archive Manager แล้วเปิด `extracted_agent.ps1` ด้วย Text Editor พบลำดับ **Deflate → XOR → Base32 → DNS query** และ key `0penClaw!` อ่านสคริปต์เพื่อดูวิธีแปลงข้อมูล ไม่ต้อง execute สคริปต์โจทย์
![[Screenshot 2026-08-15 154258.png]]

![[poison — extracted_agent.ps1 บรรทัด GetBytes และ key]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| DNS ชื่อ `<fragment>.c<index>.s3f.sync.sfrclak.com` | ข้อมูลถูกแบ่งเป็นชิ้นและมีหมายเลข | Python parser แยก fragment แล้ว sort index |
| index 0–16 | มี 17 ชิ้น | ต่อให้ครบตามลำดับตัวเลข |
| key `0penClaw!` | ใช้ XOR key ซ้ำตามความยาวข้อมูล | UNIT → Bitwise → XOR Mask |
| Base32 อยู่ชั้นนอก | ต้องถอดก่อน XOR | UNIT โมดูล `decode_to_bytes(..., "Base32")` |
| Deflate อยู่ชั้นใน | ผล XOR ยังไม่ใช่ข้อความ | Python `zlib.decompress(..., -15)` |

packet ที่บรรทุก query ใน capture เป็น UDP จึงกรอง IPv4 protocol 17 และปลายทาง port 53

---

#### ขั้น 3 — ทำไมต้องรักษาข้อมูลเป็น bytes

Base32 ให้ข้อมูล 463 ไบต์ที่ยังผ่าน XOR อยู่ หากบังคับอ่านเป็น UTF-8 กลางทาง ไบต์ที่ไม่ใช่ข้อความอาจหาย จึงใช้ **UNIT backend แบบ bytes → Hex → XOR → bytes** แล้วค่อยอ่าน JSON หลังคลาย Deflate

---

#### ขั้น 4 — แยก DNS แล้วใช้ UNIT ถอด Base32

สร้างโฟลเดอร์ทำงานแล้วรัน **Python parser ภายนอก + UNIT `Decode.base_decoder`**:
```bash
mkdir -p /tmp/unit-poison
cd /tmp/unit-poison
```

```bash
/home/nutvv/Documents/GitHub/Unit/.venv/bin/python - <<'PYCODE'
import sys, zipfile, io, struct, re
from pathlib import Path
sys.path.insert(0, "/home/nutvv/Documents/GitHub/Unit")
from Decode.base_decoder import decode_to_bytes
with zipfile.ZipFile("/home/nutvv/Downloads/tctt2026.zip") as outer:
    packed = outer.read("tctt2026/The Poisoned Package/evidence.zip")
with zipfile.ZipFile(io.BytesIO(packed)) as z:
    def read_member(name):
        return z.read(next(n for n in z.namelist() if n == name or n.endswith("/" + name)))
    capture = read_member("network_capture.pcap")
    script = read_member("extracted_agent.ps1").decode()
key = re.search(r"GetBytes\('([^']+)'\)", script).group(1)
chunks = {}
link_type = struct.unpack_from("<I", capture, 20)[0]
pos = 24
while pos < len(capture):
    length = struct.unpack_from("<I", capture, pos + 8)[0]
    frame = capture[pos + 16:pos + 16 + length]
    pos += 16 + length
    if link_type == 228:
        ip = frame
    elif link_type == 1 and frame[12:14] == b"\x08\x00":
        ip = frame[14:]
    else:
        continue
    if ip[9] != 17:
        continue
    udp = ip[(ip[0] & 15) * 4:]
    if int.from_bytes(udp[2:4], "big") != 53:
        continue
    dns = udp[8:int.from_bytes(udp[4:6], "big")]
    if dns[2] & 0x80:
        continue
    labels, i = [], 12
    while dns[i]:
        length = dns[i]
        labels.append(dns[i+1:i+1+length].decode())
        i += length + 1
    match = re.fullmatch(r"([a-z2-7]+)\.c(\d+)\.s3f\.sync\.sfrclak\.com", ".".join(labels))
    if match:
        chunks[int(match[2])] = match[1]
encoded = "".join(chunks[i] for i in range(17)).upper()
padded = encoded + "=" * (-len(encoded) % 8)
raw = decode_to_bytes(padded, "Base32")
Path("base32-input.txt").write_text(padded)
Path("xor-input.hex").write_text(raw.hex(" "))
print("Chunks:", len(chunks), "Base32 chars:", len(encoded), "Bytes:", len(raw))
print("Key:", key)
print(raw.hex(" "))
PYCODE
```

`<I` อ่านความยาว packet แบบ little-endian; `link_type == 228` คือ raw IPv4 จึงไม่ตัด Ethernet header; `range(17)` ต่อ c0 ถึง c16; `% 8` ใช้เติม padding Base32 ให้ครบกลุ่ม; `.hex(" ")` เตรียม input ที่เก็บทุกไบต์

ผลคือ 17 chunks, Base32 741 ตัวก่อน padding และข้อมูล 463 ไบต์
![[poison — Terminal แยก DNS และ Hex 463 bytes]]

---

#### ขั้น 5 — ทำ XOR ด้วย UNIT แล้วคลาย Deflate

**Step 1 — XOR ใน GUI**

เปิด **Data Hashing → Bitwise → XOR Mask** กรอก KEY `0penClaw!` แล้ว BROWSE เปิด `/tmp/unit-poison/xor-input.hex` ดูผลในส่วน `[HEX]`
![[poison — UNIT XOR Mask key 0penClaw!]]

**Step 2 — ใช้ผล XOR แบบ bytes แล้วคลาย raw Deflate**

คำสั่งนี้เรียก XOR โมดูลเดียวกับ GUI แล้วใช้ Python zlib ภายนอก:
```bash
/home/nutvv/Documents/GitHub/Unit/.venv/bin/python - <<'PYCODE'
import sys, zlib, json
from pathlib import Path
sys.path.insert(0, "/home/nutvv/Documents/GitHub/Unit")
from Tools.extra_tools import bitwise_mask
rendered = bitwise_mask(Path("xor-input.hex").read_text(), "0penClaw!", "xor")
hex_line = rendered.split("[HEX]\n", 1)[1].splitlines()[0].replace("║", "").strip()
clear = zlib.decompress(bytes.fromhex(hex_line), -15)
Path("decoded-ctf-loot.json").write_bytes(clear)
print(clear.decode())
print(json.loads(clear)["loot"]["SECRET_API_KEY"])
PYCODE
```

`-15` ระบุ raw Deflate ที่ไม่มี zlib wrapper; `bytes.fromhex` คืนข้อมูลดิบจากผล XOR; `write_bytes` บันทึก JSON ที่คลายแล้วโดยไม่เปลี่ยนไบต์

---

#### ขั้น 6 — อ่าน SECRET_API_KEY

เปิด `decoded-ctf-loot.json` ใน Text Editor ค่าใต้ `loot.SECRET_API_KEY` คือ:
```text
TCTT2026{poisoned_package_exfil_c2_tunnel}
```

![[poison — JSON loot.SECRET_API_KEY]]

---

#### ขั้น 7 — ปิดเคส

**🚩 Flag = `TCTT2026{poisoned_package_exfil_c2_tunnel}`**
