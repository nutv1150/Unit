### Slide Flow

**Secret Encoding**

---

#### ขั้น 1 — เจออะไรในไฟล์

เปิด `Secret_Encording.txt` ด้วย Text Editor พบอักขระ `I`, `l`, `_`, `|` จัดเป็นกลุ่มยาวไม่เท่ากัน ตัวอย่างต้นข้อความคือ `l_IIII_II_III`
![[Screenshot 2026-08-15 153925.png]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| `I` และ `l` มีสองชนิด | ทดลองแทนจุดและขีดของ Morse | Python: `I → .`, `l → -` |
| `_` แบ่งกลุ่มสั้น ๆ | คั่นตัวอักษร Morse | Python: split ด้วย `_` |
| `|` อยู่ระหว่างชุดคำ | คั่นคำ | Python: เปลี่ยน token นี้เป็นช่องว่าง |
| โจทย์กำหนด flag ตัวใหญ่ | รักษาตัวพิมพ์หลังถอด | โมดูล UNIT `find_first_flag` ค้นรูปแบบ |

`l_IIII_II_III` → `- / .... / .. / ...` → **THIS** ทำให้เลือกถอดเป็น Morse ต่อ

---

#### ขั้น 3 — ถอด Morse แล้วแทนคำวงเล็บ

ใช้ **Python ภายนอก** สำหรับแทนสัญลักษณ์และถอด Morse ส่วน **UNIT โมดูล `Tools.flag_detector`** ใช้ดึง flag ตอนท้าย รันใน Terminal:
```bash
/home/nutvv/Documents/GitHub/Unit/.venv/bin/python - <<'PYCODE'
import sys, zipfile
sys.path.insert(0, "/home/nutvv/Documents/GitHub/Unit")
from Tools.flag_detector import find_first_flag
with zipfile.ZipFile("/home/nutvv/Downloads/tctt2026.zip") as z:
    raw = z.read("tctt2026/Secret Encoding/Secret_Encording.txt").decode("utf-8-sig").strip()
codes = ".- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --..".split()
table = dict(zip(codes, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
table.update(dict(zip("----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----.".split(), "0123456789")))
table.update({".-.-.-": ".", "-.--.": "(", "-.--.-": ")", "..--.-": "_"})
tokens = raw.translate(str.maketrans({"I": ".", "l": "-"})).split("_")
text = "".join(" " if token == "|" else table[token] for token in tokens)
print(text)
text = text.replace("(OPENBRACESSYMBOL)", "{").replace("(CLOSEBRACESSYMBOL)", "}")
print(text)
print(find_first_flag(text))
PYCODE
```

`-` ให้ Python อ่านโค้ดจาก stdin; `utf-8-sig` อ่านข้อความพร้อมจัดการ BOM; `sys.path.insert` ให้ import โมดูล UNIT จากโปรเจกต์ได้

`table[token]` แปลงกลุ่ม Morse เป็นอักษร และ `replace` เปลี่ยนคำบอกวงเล็บเป็นเครื่องหมายจริง
![[secret — Python ถอด Morse และข้อความก่อนแทนวงเล็บ]]

---

#### ขั้น 4 — ผลลัพธ์ที่ได้

ก่อนแทนวงเล็บ:
```text
THIS IS THE SECRET MESSAGE. THE FLAG IS TCTT2026(OPENBRACESSYMBOL)S3CR3TXENC0D1NG(CLOSEBRACESSYMBOL)
```

แทน `(OPENBRACESSYMBOL)` → `{` และ `(CLOSEBRACESSYMBOL)` → `}` จึงได้:
```text
THIS IS THE SECRET MESSAGE. THE FLAG IS TCTT2026{S3CR3TXENC0D1NG}
```

![[secret — ข้อความหลังแทนวงเล็บและ flag]]

---

#### ขั้น 5 — ปิดเคส

**🚩 Flag = `TCTT2026{S3CR3TXENC0D1NG}`**
