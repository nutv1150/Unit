### Slide Flow

**Hidden Data**

---

#### ขั้น 1 — เจออะไรในไฟล์

`Challenge_Hidden_Data.txt` ยาว 9,462,027 ไบต์ ถอด **Reverse → Base64** แล้วได้ไฟล์ไบนารี 7z ขนาด 7,096,516 ไบต์
![[Screenshot 2026-08-15 153632.png]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| ข้อความต้นทางมี UTF-8 BOM | ต้องอ่าน BOM ออกก่อนกลับข้อความ | Python ใช้ utf-8-sig |
| Reverse แล้วถอด Base64 ได้ signature 7z | เป็นการซ้อน encoding ก่อน archive | UNIT โมดูล Reverse + Base64 bytes |
| `37 7A BC AF 27 1C` | signature ของ 7-Zip | UNIT File Inspection → Header Check |
| next-header CRC ไม่ตรงตำแหน่งที่ประกาศ | ต้องหาตำแหน่ง header จากข้อมูลจริง | Python ค้นหน้าต่าง 106 bytes ที่ CRC ตรง |

---

#### ขั้น 3 — ถอดไฟล์ด้วยโมดูล UNIT แล้วปรับ offset

ใช้ **Python เรียก UNIT `decode_data` และ `decode_to_bytes`** ส่วนการอ่าน header/CRC ใช้ struct และ zlib ภายนอก:
```bash
mkdir -p /tmp/unit-hidden
cd /tmp/unit-hidden
```

```bash
/home/nutvv/Documents/GitHub/Unit/.venv/bin/python - <<'PYCODE'
import sys, zipfile, struct, zlib
from pathlib import Path
sys.path.insert(0, "/home/nutvv/Documents/GitHub/Unit")
from Decode.base_decoder import decode_data, decode_to_bytes
with zipfile.ZipFile("/home/nutvv/Downloads/tctt2026.zip") as z:
    raw = z.read("tctt2026/HIdden data/Challenge_Hidden_Data.txt").decode("utf-8-sig").strip()
b = decode_to_bytes(decode_data(raw, "Reverse"), "Base64")
Path("decoded-original.7z").write_bytes(b)
offset, size, crc = struct.unpack_from("<QQI", b, 12)
found = [i for i in range(max(32, len(b)-10000), len(b)-size+1) if zlib.crc32(b[i:i+size]) == crc]
print("Bytes:",len(b),"Magic:",b[:6].hex(" "))
print("Declared offset:", offset, "Header size:", size, "Matching positions:", found)
if len(found) == 1:
    fixed = bytearray(b)
    struct.pack_into("<Q", fixed, 12, found[0]-32)
    struct.pack_into("<I", fixed, 8, zlib.crc32(fixed[12:32]))
    Path("analysis-header-repointed.7z").write_bytes(fixed)
    print("New relative offset:", found[0]-32)
PYCODE
```

`Reverse` กลับข้อความก่อนถอด; `decode_to_bytes` เก็บผล Base64 เป็น bytes; `<QQI` อ่าน offset/size/CRC แบบ little-endian; `found[0]-32` แปลงตำแหน่ง absolute เป็น offset ตามรูปแบบ 7z

ไฟล์ที่ถอดได้เก็บเป็น decoded-original.7z และไฟล์ทดลองปรับ header เก็บแยกเป็น analysis-header-repointed.7z
![[hidden — ผล Reverse Base64 และค่า header offset]]

---

#### ขั้น 4 — ดู header ด้วย UNIT และเปิดด้วย 7-Zip

**Step 1 — UNIT File Inspection → Header Check**

เลือก `/tmp/unit-hidden/decoded-original.7z` แล้วเริ่มวิเคราะห์ จะเห็น signature 7z
![[hidden — UNIT Header Check signature 37 7A BC AF 27 1C]]

**Step 2 — 7-Zip ภายนอกอ่านไฟล์ที่ปรับ header**
```bash
7z t analysis-header-repointed.7z
```

`t` สั่งให้ 7-Zip อ่านและคลายข้อมูลเพื่อตรวจความสมบูรณ์ของ archive โดยไม่เขียนไฟล์ภายในออกมา

---

#### ขั้น 5 — ผลลัพธ์ของไฟล์ที่กู้ได้

ตำแหน่ง header ที่พบคือ absolute 7,096,410 จึงเปลี่ยน relative offset เป็น 7,096,378 แล้วได้ผลจาก 7-Zip:
```text
Data Error: HiddenFlag.jpg
```

ชื่อ HiddenFlag.jpg อ่านได้จาก archive แต่ข้อมูลบีบอัดของภาพยังเกิด Data Error จึงไม่มีภาพที่ถอดสำเร็จให้อ่านข้อความต่อ
![[hidden — 7-Zip Data Error ที่ HiddenFlag.jpg]]
