### Slide Flow

**Stupid Encryption**

---

#### ขั้น 1 — เจออะไรในไฟล์

ใช้ **Archive Manager** เปิด `/home/nutvv/Downloads/tctt2026.zip` → กด **Extract** → เลือกโฟลเดอร์ปลายทาง แล้วเข้าโฟลเดอร์โจทย์ `Stupid Encryption`

ใช้ UNIT **Data Hashing → Decode → Base64 → BROWSE** เปิด `StupidEncryption.txt` ในโฟลเดอร์ Stupid Encryption ผลที่ได้ยังไม่เป็นประโยค แต่กลายเป็นคู่สัญลักษณ์ เช่น `FG EC EF`
![[Screenshot 2026-08-15 154004.png]]

![[stupid — UNIT ผล Base64 เป็นคู่สัญลักษณ์]]

---

#### ขั้น 2 — แปลความหมาย hint ทีละจุด

| สิ่งที่สังเกตเห็น | แปลว่า | ใช้ยังไง (UNIT/แอปนอก) |
| --- | --- | --- |
| มีอักขระ `ABCDEFGHIJefghij` รวม 16 ชนิด | เป็นเบาะแสของ Hex ที่แทนชื่อ nibble | กำหนด Alphabet ใน UNIT → Hex |
| ข้อมูลจัดเป็นคู่ | สองหลัก Hex แทน 1 byte | แทนสัญลักษณ์ก่อนประกอบ bytes |
| ตารางแรกยังให้ข้อความไม่เป็นประโยค | ต้องใช้ตารางที่สองร่วมด้วย | รวมสองตารางเป็น Alphabet เดียว |
| I ใหญ่กับ i เล็กเป็นคนละตัว | ตัวพิมพ์มีผลต่อค่า | คัดลอก Alphabet ตามตัวพิมพ์จริง |

การเห็น 16 ชนิดช่วยตั้งสมมติฐาน แต่ตารางแทนค่ามาจากการทดลองถอด ไม่ได้บอกได้จากจำนวนอักขระอย่างเดียว

---

#### ขั้น 3 — รวมตารางสองชั้น

ตารางที่ใช้ถอดคือ:
```text
ตาราง 1
ABCDEFGHIJefghij → 0123456789ABCDEF

ตาราง 2
0123456789ABCDEF → 0987654321FEDCBA
```

เมื่อรวมสองชั้นแล้ว เรียงสัญลักษณ์ต้นทางตามผลลัพธ์ `0123456789ABCDEF` จะได้:
```text
AJIHGFEDCBjihgfe
```

ตัวอย่าง `FG` → `54`, `EC` → `68`, `EF` → `65` จึงอ่านเป็น `The`

---

#### ขั้น 4 — ถอด Hex ใน UNIT

**Step 1 — ย้ายผล Base64 มาเป็น INPUT**

เลือกข้อความ OUTPUT ทั้งหมดแล้วคัดลอกมาแทน INPUT_STREAM

**Step 2 — เลือก Hex และกรอก Alphabet**

เปิด **Data Hashing → Decode → Hex** เปลี่ยน ALPHABET จากค่าปกติเป็น:
```text
AJIHGFEDCBjihgfe
```

ช่องนี้ระบุว่าสัญลักษณ์ใดแทนค่า 0–F ตามตำแหน่ง ตัวถอดข้ามช่องว่างและขึ้นบรรทัดใหม่ให้ HEX PREVIEW จะแสดงเลขฐานสิบหกหลังแทนค่า
![[stupid — Hex พร้อม Alphabet AJIHGFEDCBjihgfe]]

---

#### ขั้น 5 — อ่านข้อความที่ถอดได้

OUTPUT เริ่มต้นว่า:
```text
The lazy coder stared at the blinking cursor, hoping the program might write itself.
```

เลื่อนอ่านข้อความต่อจนถึง `Flag is TCTT2026{XLAZYXC0D3RX}` โดย `0` ใน `C0D3R` เป็นเลขศูนย์
![[stupid — ข้อความสุดท้ายและ flag ใน UNIT]]

---

#### ขั้น 6 — ปิดเคส

**🚩 Flag = `TCTT2026{XLAZYXC0D3RX}`**
