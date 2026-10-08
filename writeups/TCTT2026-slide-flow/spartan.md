### Slide Flow

**Phantom Spartan**

---

#### ขั้น 1 — เจออะไรในไฟล์

ไฟล์ `phantom_spartan.pcap` เป็น raw IPv4 (link type 228) มี 151 packets ส่วนที่ซ่อนข้อมูลคือ UDP ปลายทาง 9999 จำนวน 50 packets payload ละหนึ่งไบต์

ใช้ Python อ่าน packet inventory จาก `spartan/inspection.json` ที่แยกจาก capture โดยแตกไฟล์ประกอบก่อน:
```bash
mkdir -p /tmp/unit-spartan
cd /tmp/unit-spartan
unzip -q "/home/nutvv/Downloads/write up.zip" "spartan/*" -d .
```

`-q` ลดข้อความระหว่างแตกไฟล์, `"spartan/*"` เลือกเฉพาะเคสนี้ และ `-d .` วางไฟล์ในโฟลเดอร์ทำงาน

![[spartan — UDP port 9999 และ IP ID ใน packet list]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| payload ละ 1 byte | ต้องต่อข้อมูลหลาย packets | Python รวม payload_hex |
| IP ID ครบ 0–49 แต่ไม่ได้เรียงมา | IP ID บอกตำแหน่งแต่ละ byte | เรียงด้วย key=ip_id |
| ICMP TTL 25 ต่างจากกลุ่มส่วนใหญ่ | เป็นเบาะแสให้ทดลองค่า XOR | UNIT → XOR Mask ใช้ `0x25` |
| ชื่อ Spartan | ชวนให้ลอง Scytale/transposition | Python อ่านตำแหน่งคู่แล้วคี่ |

`25` ฐานสิบกับ `0x25` ฐานสิบหกเป็นคนละค่า การถอดชุดนี้ใช้ **0x25 = 37 ฐานสิบ**

---

#### ขั้น 3 — เรียงข้อมูลแล้วทำ XOR

**Step 1 — Python ภายนอกเรียง IP ID**
```bash
python3 - <<'PYCODE'
import json
from pathlib import Path
r = json.loads(Path("spartan/inspection.json").read_text())
rows = sorted((x for x in r["rows"] if x.get("dport") == 9999), key=lambda x: x["ip_id"])
data = bytes.fromhex("".join(x["payload_hex"] for x in rows))
Path("spartan-input.hex").write_text(data.hex(" "))
print("Packets:", len(rows), "Bytes:", len(data))
print(data.hex(" "))
PYCODE
```

`sorted(..., key=...)` เรียงตามเลข IP ID และ `bytes.fromhex` คืน payload เป็นข้อมูลดิบ 50 ไบต์

**Step 2 — UNIT หมวด Bitwise**

เปิด **Data Hashing → Bitwise → XOR Mask** ใส่ KEY `0x25` แล้ว BROWSE เปิด `/tmp/unit-spartan/spartan-input.hex` ผลข้อความคือ:
```text
I0TN_1MDS4US__ATNHN3I_VW2050{DS3PN4}R_T_4_N___L_3_
```

![[spartan — UNIT XOR Mask key 0x25 และ output]]

---

#### ขั้น 4 — อ่านตำแหน่งคู่ก่อนคี่

ใช้ **Python ภายนอก** จัดอักษรหลัง XOR ตาม transposition:
```bash
python3 - <<'PYCODE'
text = 'I0TN_1MDS4US__ATNHN3I_VW2050{DS3PN4}R_T_4_N___L_3_'
plain = text[::2] + text[1::2]
print(plain)
PYCODE
```

`text[::2]` อ่าน index 0,2,4,… และ `text[1::2]` อ่าน index 1,3,5,… ต่อสองชุดแล้วได้:
```text
IT_MSU_ANNIV25{SP4RT4N_L30N1D4S_TH3_W00D3N}_______
```

underscore หลัง `}` เป็น padding เลือก flag ถึงวงเล็บปิดเท่านั้น
![[spartan — ผล transposition และ flag]]

---

#### ขั้น 5 — ปิดเคส

**🚩 Flag = `IT_MSU_ANNIV25{SP4RT4N_L30N1D4S_TH3_W00D3N}`**
